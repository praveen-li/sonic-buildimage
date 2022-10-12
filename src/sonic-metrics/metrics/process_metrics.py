#!/usr/bin/python

"""
    ProcessInfoUpdateTask:

    Process information update Task for metrics daemon in SONiC.
    'ProcessInfoUpdateTask' will loop to collect process related information and
    write the information to state DB.

    So the process information just includes two things:
                        1.	Presence
                        2.	Up_time

"""

try:
    import psutil
    import json
    import yaml
    import ast
    import subprocess
    import shlex
    import time
    import os
    import re
    import threading
    import operator
    from datetime import datetime

    from swsssdk import SonicV2Connector
    from metrics import util
    from metrics.logger import Logger

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


#
# ====================== Constants =======================================
#

SYSLOG_IDENTIFIER = "process_metrics"
log = Logger(SYSLOG_IDENTIFIER)
log.set_priority_info()

CRITICAL_PROCESSES_FILE = os.path.join(os.path.dirname(__file__), 'data/critical_process_file.json')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data/config.yml')

PROCESS_INFO_TABLE = 'PROCESS_INFO'
TOP_PROC_SORTBY_CPU_TABLE = 'TOP_PROCESS_SORTBY_CPU'
TOP_PROC_SORTBY_MEMORY_TABLE = 'TOP_PROCESS_SORTBY_MEMORY'
PROCESS_INFO_UPDATE_PERIOD_SECS = 30
DEFAULT_REL_VERSION = '3'
PROC_NAME_MAX_SLICE = 4
PROC_NAME_MAX_CHAR = 30
DEFAULT_PROCESS_LOOP = 10
TABLE_NAME_SEPARATOR = '|'

# Process State definition
STATE_RUNNING = 1
STATE_NOT_RUNNING = 0


class ProcessInfoUpdateTask(object):
    """
    Base class for Critical Process Task Update. It collects critical process info for every 30 sec,
    and stores information to state DB after the check.
    """

    def __init__(self):
        self.task_thread = None
        self.task_stopping_event = threading.Event()
        self._db = None


    def readJson(self, filename):
        # Read critical process file
        try:
            with open(filename) as fp:
                try:
                    data = json.load(fp)
                except Exception as e:
                    log.error("error occurred while parsing json: {}".format(e))
                    return
            data_dict = ast.literal_eval(json.dumps(data))
            return data_dict
        except Exception as e:
            log.error("Json file {} does not exist".format(filename))
            return

    def load_config_file(self):
        try:
            with open(CONFIG_FILE) as conf_file:
                confInfo = yaml.load(conf_file, Loader=yaml.FullLoader)
            return confInfo
        except IOError as e:
            log.error("Error: {}".format(str(e)))
            log.error("Not found config file, please add a config file manually")
            return

    def get_full_procName(self, proc):
        cmdline = proc.cmdline()
        if proc.name().startswith('python'):
            # Get full process name within the list slice and char limitation
            proc_name_full = ' '.join(cmdline[:PROC_NAME_MAX_SLICE])
            return proc_name_full[:PROC_NAME_MAX_CHAR]
        return proc.name()

    def checkIfProcessRunning(self, processName):
        '''
        Check if there is any running process that contains the given name processName.
        '''
        # Iterate over the all the running process
        for proc in psutil.process_iter(["cmdline", "status", "pid"]):
            try:
                fullcmd = ' '.join([str(elem) for elem in proc.cmdline()])

                # Check if processName is in any of the running/sleeping process.
                if (processName in fullcmd and proc.status() in ["running", "sleeping"]):
                    pid = proc.pid
                    return STATE_RUNNING, pid

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return STATE_NOT_RUNNING, None


    def checkProcesses(self, pro_list):
        '''
        Build procces info map to iterate over during REDIS DB Update
        '''
        process_dict = dict()

        for proc in pro_list:
            process_dict[proc] = dict()

            # Get Status and PID for each process
            status, pid = self.checkIfProcessRunning(proc)

            process_dict[proc]["status"] = status
            process_dict[proc]["pid"] = pid
        return process_dict


    def update_process_info(self):
        """
        Update crtical process status and uptime to state DB under PROCESS_INFO_TABLE table
        """

        critical_process_info = self.readJson(CRITICAL_PROCESSES_FILE)
        if not critical_process_info:
            log.error("oerror occurred while parsing json file {}".format(CRITICAL_PROCESSES_FILE))
            return

        rel, major, minor = util.check_version()
        log.debug("SONiC Release {}, manjor {}, minor {} version".format(rel, major, minor))
        if not rel:
            # if check_version regex does not match, pin it to dafault release version
            rel =  DEFAULT_REL_VERSION

        ver_key = "v_{}.x".format(rel)


        if ver_key not in critical_process_info.keys():
            ver_key = "v_{}.x".format(DEFAULT_REL_VERSION)

        critical_process_dict = critical_process_info[ver_key]
        pro_list = list()
        for dock, process in  critical_process_dict.items():
            pro_list.extend(process)

        process_dict = self.checkProcesses(pro_list)
        if not process_dict:
            log.error("Unable to get process info")
            return

        for process in process_dict.keys():
            # Connect to STATE_DB and create process info tables
            proc_key =  PROCESS_INFO_TABLE + "|{}".format(process)

            status, pid = process_dict[process]["status"], process_dict[process]["pid"]

            # Store status info to each process table.
            self._db.set(self._db.STATE_DB, proc_key, "status", status)

            if status == STATE_RUNNING:
                if pid is None:
                    log.error("Unable to get PID info")
                    return
                try:
                    p = psutil.Process(pid)
                    elapsedTime = time.time() - p.create_time()
                except:
                    log.info("Process {} not found".format(process))
                    pass
            else:
                elapsedTime = "N/A"

            # Store uptime info to each process table.
            self._db.set(self._db.STATE_DB, proc_key, "up_time", elapsedTime)

    def get_process_list_sorted_by_cpu(self, allProcList):
        '''
        Get list of running process sorted by CPU Usage
        '''
        sorted_by_cpu_procs = []

        # Sort list of dict by key cpu_percent i.e. cpu usage
        sorted_by_cpu_procs = sorted(allProcList, key=lambda procObj: procObj['cpu_percent'], reverse=True)
        return sorted_by_cpu_procs

    def get_process_list_sorted_by_memory(self, allProcList):
        '''
        Get list of running process sorted by Memory Usage
        '''
        sorted_by_memory_procs = []

        # Sort list of dict by key vms i.e. memory usage
        sorted_by_memory_procs = sorted(allProcList, key=lambda procObj: procObj['vms'], reverse=True)
        return  sorted_by_memory_procs


    def update_top_process(self):
        '''
        Top Talker: Update top n process to state DB
        -.-.-.-.-.-
        1. Update top n process sort by CPU under TOP_PROCESS_SORTBY_MEMORY table
        2. Update top n process sort by Memory under TOP_PROCESS_SORTBY_CPU table
        '''
        confInfo = self.load_config_file()
        if not confInfo:
            log.error("Error occurred while parsing config file {}".format(CONFIG_FILE))
            log.info("Taking deafult value instead: {}".format(DEFAULT_PROCESS_LOOP))
            process_loop = int(DEFAULT_PROCESS_LOOP)
        else:
            # Configurable Process Loop; otherwise take default value
            process_loop = int(confInfo.get('process_loop', DEFAULT_PROCESS_LOOP))

        # Return an iterator yielding a Process class for all running processes
        psutil.cpu_percent(interval=None)
        procs = psutil.process_iter()
        allProcList = []
        for proc in procs:
            try:
                procInfo = proc.as_dict(attrs=['name', 'memory_percent', 'memory_info', 'cpu_percent'])
                procInfo['name'] =  self.get_full_procName(proc)
                procInfo['vms'] = proc.memory_info().vms / (1024 * 1024)
                procInfo['cpu_percent'] = proc.cpu_percent(0.5)
                allProcList.append(procInfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        listOfProcPerCPU = self.get_process_list_sorted_by_cpu(allProcList)
        listOfProcPerMemory = self.get_process_list_sorted_by_memory(allProcList)

        # Wipe out 'TOP_PROCESS_SORTBY_MEMORY' table from state_db before updating
        self._db.delete_all_by_pattern(self._db.STATE_DB, "TOP_PROCESS_SORTBY_MEMORY|*")

        mem_proc_loop = 1
        for elem in  listOfProcPerMemory[:process_loop]:
            # Create 'TOP_PROCESS_SORTBY_MEMORY' table with process name.

            proc_name, memory_percent = elem['name'], elem['memory_percent']
            mem_pos_key = TABLE_NAME_SEPARATOR + "memory_top{}".format(str(mem_proc_loop))
            mem_procname_key = TABLE_NAME_SEPARATOR + str(proc_name)
            proc_key =  TOP_PROC_SORTBY_MEMORY_TABLE + mem_pos_key + mem_procname_key

            # Connect to STATE_DB, Add process key with Name and Store memory percent info.
            self._db.set(self._db.STATE_DB, proc_key, "memory_percent", memory_percent)

            mem_proc_loop += 1

        # Wipe out 'TOP_PROCESS_SORTBY_CPU' table from state_db before updating
        self._db.delete_all_by_pattern(self._db.STATE_DB, "TOP_PROCESS_SORTBY_CPU|*")

        cpu_proc_loop = 1
        for elem in  listOfProcPerCPU[:process_loop]:

            # Create 'TOP_PROCESS_SORTBY_CPU' table with process name.
            proc_name, cpu_percent =   elem['name'], elem['cpu_percent']
            cpu_pos_key = TABLE_NAME_SEPARATOR + "cpu_top{}".format(str(cpu_proc_loop))
            cpuproc_name_key = TABLE_NAME_SEPARATOR + str(proc_name)
            proc_key =  TOP_PROC_SORTBY_CPU_TABLE + cpu_pos_key + cpuproc_name_key

            # Connect to STATE_DB, Add process key with Name and Store CPU percent info.
            self._db.set(self._db.STATE_DB, proc_key, "cpu_percent", cpu_percent)

            cpu_proc_loop += 1


    def task_worker(self):
        # Start loop to update critical process info in DB periodically
        log.info("Start process info update loop")

        while not self.task_stopping_event.wait(PROCESS_INFO_UPDATE_PERIOD_SECS):
            self.update_process_info()
            self.update_top_process()

        log.info("Stop process info update loop")


    def task_run(self, db):
        if self.task_stopping_event.is_set():
            return

        self._db = db
        self.task_thread = threading.Thread(target=self.task_worker)
        self.task_thread.start()


    def task_stop(self):
        self.task_stopping_event.set()
        self.task_thread.join()

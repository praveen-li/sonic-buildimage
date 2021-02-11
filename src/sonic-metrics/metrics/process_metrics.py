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
    import ast
    import subprocess
    import shlex
    import time
    import os
    import re
    import threading
    from datetime import datetime

    from swsssdk import SonicV2Connector
    from metrics import util

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


#
# ====================== Constants =======================================
#


CRITICAL_PROCESSES_FILE = os.path.join(os.path.dirname(__file__), 'data/critical_process_file.json')

PROCESS_INFO_TABLE = 'PROCESS_INFO'
PROCESS_INFO_UPDATE_PERIOD_SECS = 30
DEFAULT_REL_VERSION = '2'

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


    def deinit(self):
        """
        Destructor. Remove all entries in 'PROCESS_INFO' table.
        :return:
        """
        self._clear_process_info_table()

    def _clear_process_info_table(self):
        self._db.delete_all_by_pattern(self._db.STATE_DB, "PROCESS_INFO|*")


    def readJson(self, filename):
        # Read critical process file
        try:
            with open(filename) as fp:
                try:
                    data = json.load(fp)
                except Exception as e:
                    util.log_error("error occurred while parsing json: {}".format(e))
                    return
            data_dict = ast.literal_eval(json.dumps(data))
            return data_dict
        except Exception as e:
            util.log_error("Json file {} does not exist".format(filename))
            return


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
        util.log_info("Start Critical Processs Monitoring loop")

        critical_process_info = self.readJson(CRITICAL_PROCESSES_FILE)
        if not critical_process_info:
            util.log_error("oerror occurred while parsing json file {}".format(CRITICAL_PROCESSES_FILE))
            return

        rel, major, minor = util.check_version()
        util.log_info("SONiC Release {}, manjor {}, minor {} version".format(rel, major, minor))
        if not rel:
            util.log_error("Unable to get release version")
            return

        ver_key = "v_{}.x".format(rel)


        if ver_key not in critical_process_info.keys():
            ver_key = "v_{}.x".format(DEFAULT_REL_VERSION)

        critical_process_dict = critical_process_info[ver_key]
        pro_list = list()
        for dock, process in  critical_process_dict.items():
            pro_list.extend(process)

        process_dict = self.checkProcesses(pro_list)
        if not process_dict:
            util.log_error("Unable to get process info")
            return

        for process in process_dict.keys():
            # Connect to STATE_DB and create process info tables
            proc_key =  PROCESS_INFO_TABLE + "|{}".format(process)

            status, pid = process_dict[process]["status"], process_dict[process]["pid"]

            # Store status info to each process table.
            self._db.set(self._db.STATE_DB, proc_key, "status", status)

            if status == STATE_RUNNING:
                if pid is None:
                    util.log_error("Unable to get PID info")
                    return
                p = psutil.Process(pid)
                elapsedTime = time.time() - p.create_time()
            else:
                elapsedTime = "N/A"

            # Store uptime info to each process table.
            self._db.set(self._db.STATE_DB, proc_key, "up_time", elapsedTime)


    def task_worker(self):
        # Start loop to update critical process info in DB periodically
        util.log_info("Start process info update loop")

        while not self.task_stopping_event.wait(PROCESS_INFO_UPDATE_PERIOD_SECS):
            self.update_process_info()

        util.log_info("Stop process info update loop")

        # Remove all entries in 'PROCESS_INFO' table.
        self.deinit()

        self._db.close(self._db.STATE_DB)
        util.log_info("Stop process info update loop")


    def task_run(self, db):
        if self.task_stopping_event.is_set():
            return

        self._db = db
        self.task_thread = threading.Thread(target=self.task_worker)
        self.task_thread.start()


    def task_stop(self):
        self.task_stopping_event.set()
        self.task_thread.join()

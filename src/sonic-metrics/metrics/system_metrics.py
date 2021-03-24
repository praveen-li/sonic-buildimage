#!/usr/bin/python

"""
    SystemInfoUpdateTask:

    System information update Task for metrics daemon in SONiC.
    'SystemInfoUpdateTask' will loop to collect system related information and
    write the information to state DB.

    So the system information includes:
                        1.	sysDescr
                        2.	sysUpTime

"""

try:
    import subprocess
    import shlex
    import threading
    import os
    import time

    from swsssdk import SonicV2Connector, ConfigDBConnector
    from metrics import util

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


#
# ====================== Constants =======================================
#

SYSTEM_INFO_TABLE = 'SYSTEM_INFO'
SYSTEM_INFO_UPDATE_PERIOD_SECS = 60
STAT_KEY = 'STAT'

SYS_UPTIME_FIELD = 'sysUpTime'
SYS_DESC_FIELD = 'sysDescr'
SYS_NAME_FIELD = 'sysName'
RUN_CONF_CHANGED_FIELD = 'RunningConfigLastChanged'
RUN_CFG_FILE = "/etc/sonic/config_db.json"


class SystemInfoUpdateTask(object):
    """
    Base class for System Task Update. It collects few system info for every 60 sec,
    and stores information to state DB after the check.
    """

    def __init__(self):
        self.task_thread = None
        self.task_stopping_event = threading.Event()
        self._db = None


    def deinit(self):
        """
        Destructor. Remove all entries in 'SYSTEM_INFO' table.
        :return:
        """
        self._clear_system_info_table()


    def _clear_system_info_table(self):
        self._db.delete_all_by_pattern(self._db.STATE_DB, "SYSTEM_INFO|*")


    def get_localhost_info(self,field):
        try:
            config_db = ConfigDBConnector()
            config_db.connect()

            metadata = config_db.get_table('DEVICE_METADATA')

            if 'localhost' in metadata and field in metadata['localhost']:
                return metadata['localhost'][field]
        except Exception:
            pass

        return None


    def get_hostname(self):
        '''
        Get system Name
        '''
        return self.get_localhost_info('hostname')


    def get_hwsku(self):
        '''
        Get system HWSKU
        '''
        return self.get_localhost_info('hwsku')


    def get_sys_uptime(self):
        '''
        Get system uptime
        '''
        sys_uptime_cmd = 'cat /proc/uptime'
        awk_uptime_cmd = 'awk "{print $1}"'
        try:
            process = subprocess.Popen(
                shlex.split(sys_uptime_cmd), shell=False, stdout=subprocess.PIPE)
            # uptime second
            uptime_out = subprocess.Popen(
                shlex.split(awk_uptime_cmd), stdin=process.stdout, stdout=subprocess.PIPE)
            output, _ = uptime_out.communicate()
            return output

        except Exception as e:
            util.log_error("Cannot get Uptime with error {}".format(e))
            return


    def get_build_info(self):
        '''
        Get sonic info using sonic_version.yml file
        '''
        sys_build_info = util.get_sonic_version_info()
        return sys_build_info


    def get_sys_desc(self):
        '''
        Get decsription info using config db and sonic_version.yml file
        '''
        build_version, hwsku, debian_version, kernel_version = '', '', '', ''
        sys_build_info = self.get_build_info()

        if sys_build_info:
            build_version = sys_build_info['build_version']
            debian_version = sys_build_info['debian_version']
            kernel_version = sys_build_info['kernel_version']
        else:
            util.log_error("Error occurred while parsing build data")
            return

        hwsku = self.get_hwsku()
        if not hwsku:
            util.log_error("Error occurred while parsing hwsku data")
            return

        # Get Description of the system and sw running
        sys_Desc_info = "SONiC Software Version: SONiC.{} - HwSku: {} - Distribution: Debian {}". \
                        format(build_version, hwsku, debian_version, kernel_version)

        return sys_Desc_info


    def get_run_config_modify_time(self):
        '''
        Get last modified date ins seconds for config_db.json file
        '''
        last_modified_time = ''
        if os.path.isfile(RUN_CFG_FILE):
            last_modified_time = os.stat(RUN_CFG_FILE).st_mtime
        else:
            util.log_error("{} file not Exist".format(RUN_CFG_FILE))
        return last_modified_time


    def update_system_info(self):
        '''
        Update system information and uptime to state DB under SYSTEM_INFO_TABLE table
        '''
        util.log_info("Start updating system Info")

        stat_key =  SYSTEM_INFO_TABLE + "|{}".format(STAT_KEY)

        # Get system uptime
        output = self.get_sys_uptime()
        if not output:
            util.log_error("Error occurred while parsing uptime data")
            return
        sys_uptime = output.strip()

        # Store system uptime info to `SYSTEM_INFO_TABLE` table.
        self._db.set(self._db.STATE_DB, stat_key, SYS_UPTIME_FIELD, sys_uptime)

        # Get system Name
        sysName_res = self.get_hostname()
        if not sysName_res:
            util.log_error("Error occurred while parsing system Naming data")
            return
        sysName = sysName_res.strip()

        # Store system Name info to `SYSTEM_INFO_TABLE` table.
        self._db.set(self._db.STATE_DB, stat_key, SYS_NAME_FIELD, sysName)

        # Create fv_map with help of `sonic_version.yml` data file
        fv_map = dict()
        field_list = [ 'build_version', 'debian_version', 'kernel_version', 'asic_type']

        sys_desc_info = self.get_sys_desc()
        if not sys_desc_info:
            util.log_error("Unable to get system description info")
            return
        self._db.set(self._db.STATE_DB, stat_key, SYS_DESC_FIELD, sys_desc_info)


        sys_build_info = self.get_build_info()
        # Get System info about build_version, debian_version, kernel_version, asic_type
        for field in field_list:
            fv_map[field] = sys_build_info[field]

        if len(fv_map.keys()) == 0:
            util.log_error("Key Value is missing. Available keys:{}".format(fv_map.keys()))
            return

        # Store system build info to 'SYSTEM_INFO' table.
        for field, value in fv_map.items():
            self._db.set(self._db.STATE_DB, stat_key, field, value)

        changed_time = ''
        cur_time = time.time()
        modified_time =  self.get_run_config_modify_time()
        if modified_time:
            changed_time = cur_time - modified_time
        else:
            util.log_error("Unable to get modified time info")
            return

        # Store the value of sysUpTime when the running configuration was last changed
        self._db.set(self._db.STATE_DB, stat_key, RUN_CONF_CHANGED_FIELD, changed_time)


    def task_worker(self):
        # Start loop to update system info in DB periodically
        util.log_info("Start system info update loop")

        while not self.task_stopping_event.wait(SYSTEM_INFO_UPDATE_PERIOD_SECS):
            self.update_system_info()

        util.log_info("Stop system info update loop")

        # Remove all entries in 'SYSTEM_INFO' table.
        self.deinit()

        self._db.close(self._db.STATE_DB)
        util.log_info("Stop system info update loop")


    def task_run(self, db):
        if self.task_stopping_event.is_set():
            return

        self._db = db
        self.task_thread = threading.Thread(target=self.task_worker)
        self.task_thread.start()


    def task_stop(self):
        self.task_stopping_event.set()
        self.task_thread.join()

import os
import fnmatch
import syslog
import fcntl,errno,time

WDT_DEV_PATH = "/dev/"
WDT_SYSFS = "/sys/class/watchdog/"
WDT_IDENTITY = "Cisco IOFPGA Watchdog"
XCVR_EEPROM_LOCK_MAX_RETRY = 5000
def get_watchdog_device():

    try:
        for filename in os.listdir("/dev/"):
            if fnmatch.fnmatch(filename, 'watchdog?'):
                with open("/{}/{}/identity".format(WDT_SYSFS, filename), 'r') as wdt_f:
                    if wdt_f.readline().strip() == WDT_IDENTITY :
                        return filename

    except IOError:
        return None

    return None


def read_str_from_file(file_path, default='', raise_exception=False):
    """
    Read string content from file
    :param file_path: File path
    :param default: Default return value if any exception occur
    :param raise_exception: Raise exception to caller if True else just return default value
    :return: String content of the file
    """
    try:
        with open(file_path, 'r') as f:
            value = f.read().strip()
    except (ValueError, IOError) as e:
        if not raise_exception:
            value = default
        else:
            raise e

    return value


def read_int_from_file(file_path, default=0, raise_exception=False):
    """
    Read content from file and cast it to integer
    :param file_path: File path
    :param default: Default return value if any exception occur
    :param raise_exception: Raise exception to caller if True else just return default value
    :return: Integer value of the file content
    """
    try:
        with open(file_path, 'r') as f:
            value = int(f.read().strip())
    except (ValueError, IOError) as e:
        if not raise_exception:
            value = default
        else:
            raise e

    return value


def write_file(file_path, content, raise_exception=False):
    """
    Write the given value to a file
    :param file_path: File path
    :param content: Value to write to the file
    :param raise_exception: Raise exception to caller if True
    :return: True if write success else False
    """
    try:
        with open(file_path, 'w') as f:
            f.write(str(content))
    except (ValueError, IOError) as e:
        if not raise_exception:
            return False
        else:
            raise e
    return True


def xcvr_eeprom_rw_lock( port_num,retry_max=XCVR_EEPROM_LOCK_MAX_RETRY):
    retry = 0
    _eeprom_lock_path = "/sys/class/mifpga/mifpga/qsfp_{}_eeprom_rw_lock"
    eeprom_lock_path = _eeprom_lock_path.format(port_num+1)
    try:
        fd = open(eeprom_lock_path, "r")
    except OSError as e:
        print("Error: unable to open file: %s" % str(e))
        return None

    while (retry < retry_max):
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except (OSError,IOError) as e:
            if ((e.errno == errno.EAGAIN) or
                        (e.errno == errno.EPERM) or
                        (e.errno == errno.EBUSY) or
                        (e.errno == errno.EWOULDBLOCK) or
                        (e.errno == errno.ETIMEDOUT) or
                        (e.errno == errno.EACCES)):
                retry += 1
                time.sleep(0.001)
                continue
            else:
                print("Error: unable to lock file: %s" % str(e))
                fd.close()
                return None
    if (retry == retry_max):
        syslog.syslog(syslog.LOG_ERR,"Unable to lock eeprom file {0}".format(port_num))
        fd.close()
        return None

    return fd

def xcvr_eeprom_rw_unlock( fd):

    if fd :
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
            fd.close()
            time.sleep(0.001)
        except OSError as e:
            syslog.syslog(syslog.LOG_ERR,"Unable to unlock eeprom file")
            return False

    return True

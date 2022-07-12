############################
# Reference: https://www.kernel.org/doc/Documentation/watchdog/watchdog-api.txt
############################


try:
    import time
    import os
    import fnmatch
    import fcntl
    import array
    import struct
    import ctypes

    from sonic_platform_base.watchdog_base import WatchdogBase
    import sonic_platform.utils as pltm_utils
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

class _timespec(ctypes.Structure):
    _fields_ = [
            ('tv_sec', ctypes.c_long),
            ('tv_nsec', ctypes.c_long)
    ]


WDR_IO_WRITE = 0x40000000
WDR_IO_READ = 0x80000000
WDR_IO_READ_WRITE = WDR_IO_WRITE | WDR_IO_READ
WDR_IO_SIZE_INT = 0x00040000
WDR_IO_TYPE_WATCHDOG = ord('W') << 8

WDIOC_SETOPTIONS  = 4  | WDR_IO_READ | WDR_IO_SIZE_INT | WDR_IO_TYPE_WATCHDOG
WDIOC_KEEPALIVE   = 5  | WDR_IO_READ | WDR_IO_SIZE_INT | WDR_IO_TYPE_WATCHDOG
WDIOC_SETTIMEOUT  = 6  | WDR_IO_READ_WRITE | WDR_IO_SIZE_INT | WDR_IO_TYPE_WATCHDOG
WDIOC_GETTIMELEFT = 10 | WDR_IO_READ | WDR_IO_SIZE_INT | WDR_IO_TYPE_WATCHDOG

WDIOS_DISABLECARD = 0x0001
WDIOS_ENABLECARD = 0x0002
WD_ERROR = -1
WDT_MAX_TIMEOUT = 508

class Watchdog(WatchdogBase):
    """ Watchdog class"""

    CLOCK_MONOTONIC = 1

    def __init__(self):
        self.wdt_dev = None
        self.wdt_name = None
        self.wdt_hdlr = None
        self.armed = False
        self.armed_time = -1
        self.timeout = -1
         
        self.wdt_name = pltm_utils.get_watchdog_device()
        if self.wdt_name is not None:
            self.wdt_dev = pltm_utils.WDT_DEV_PATH + self.wdt_name

        self.wdt_hdlr = os.open(self.wdt_dev, os.O_WRONLY)
        if self.wdt_hdlr is None:
            return WD_ERROR

        self.card_disable()

        self._librt = ctypes.CDLL('librt.so.1', use_errno=True)
        self._clock_gettime = self._librt.clock_gettime
        self._clock_gettime.argtypes=[ctypes.c_int, ctypes.POINTER(_timespec)]

    def _get_time(self):
        """
        To get clock monotonic time
        """
        ts = _timespec()
        if self._clock_gettime(self.CLOCK_MONOTONIC, ctypes.pointer(ts)) != 0:
            errno_ = ctypes.get_errno()
            return 0
        return ts.tv_sec + ts.tv_nsec * 1e-9

    def card_enable(self):
        if not self.is_armed():
            # Turn on the watchdog timer
            req = array.array('h', [WDIOS_ENABLECARD])
            fcntl.ioctl(self.wdt_hdlr, WDIOC_SETOPTIONS, req, False)
            self.armed = True
            self.armed_time  = self._get_time()
            self.timeout = WDT_MAX_TIMEOUT

    def card_disable(self):
        # Turn off the watchdog timer
        req = array.array('h', [WDIOS_DISABLECARD])
        fcntl.ioctl(self.wdt_hdlr, WDIOC_SETOPTIONS, req, False)
        self.armed = False
        self.armed_time = -1
        self.timeout = -1

    def keepalive(self):
        if self.is_armed():
            # Keep alive watchdog timer
            fcntl.ioctl(self.wdt_hdlr, WDIOC_KEEPALIVE)
            self.armed_time = self._get_time()

    def is_armed(self):
        return self.armed

    def get_remaining_time(self):
        """
        If the watchdog is armed, retrieve the number of seconds
        remaining on the watchdog timer
        Returns:
            An integer specifying the number of seconds remaining on
            their watchdog timer. If the watchdog is not armed, returns
            -1.
            Cisco platforms doesnot have hardware support to show remaining time.
            Due to this limitation, this API is implemented in software.
            This API would return correct software time difference if it
            is called from the process which armed the watchdog timer.
            If this API called from any other process, it would return
            0. If the watchdog is not armed, this API would return -1.
        """
        if not self.is_armed():
            return -1

        if self.armed_time > 0 and self.timeout != 0:
            cur_time = self._get_time()
            if cur_time <= 0:
                return 0
            diff_time = int(cur_time - self.armed_time)
            if diff_time > self.timeout:
                return self.timeout
            else:
                return self.timeout - diff_time

        return 0

    def set_timeout(self, seconds):
        # Set watchdog timer
        wdt_ticks = int(seconds / 2)
        req = array.array('I', [wdt_ticks])
        fcntl.ioctl(self.wdt_hdlr, WDIOC_SETTIMEOUT, req, True)
        self.armed = True
        self.armed_time = self._get_time()
        self.timeout = int(((seconds/2)*2))
        return int(req[0])

    def arm(self, seconds):
        err = WD_ERROR
        if seconds < 0 or seconds > WDT_MAX_TIMEOUT:
            return err

        if self.wdt_dev is None:
            return err
        
        if self.wdt_hdlr is None:
            return err

        try:
            self.card_enable()
            self.set_timeout(seconds)
        except IOError:
            pass

        return int((seconds/2)*2)

    def disarm(self):
        if self.wdt_hdlr is None:
            return False

        try:
            self.card_disable()
        except IOError:
            return False

        return True

    def __del__(self):
        err = WD_ERROR
        if self.wdt_hdlr is None:
            return err
        os.close(self.wdt_hdlr)
        self.wdt_hdlr = None


# w1 =  Watchdog()
# w1.is_armed()
# w1.arm(150)
# print("\nTime left : {}".format(w1.get_remaining_time()))
# w1.keepalive()
# w1.disarm()

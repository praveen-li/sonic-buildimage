############################
# Reference: https://www.kernel.org/doc/Documentation/watchdog/watchdog-api.txt
############################

import time
import os
import fnmatch
import fcntl
import array

try:
    from sonic_platform_base.watchdog_base import WatchdogBase
    import sonic_platform.utils as pltm_utils
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

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
WDT_MAX_TIMEOUT = 254

class Watchdog(WatchdogBase):
    """ Watchdog class"""

    def __init__(self):
        self.wdt_dev = None
        self.wdt_name = None
        self.wdt_hdlr = None
         
        self.wdt_name = pltm_utils.get_watchdog_device()
        if self.wdt_name is not None:
            self.wdt_dev = pltm_utils.WDT_DEV_PATH + self.wdt_name

        self.wdt_hdlr = os.open(self.wdt_dev, os.O_WRONLY)
        if self.wdt_hdlr is None:
            return WD_ERROR

        self.card_disable()
        self.armed = False

    def card_enable(self):
        # Turn on the watchdog timer
        req = array.array('h', [WDIOS_ENABLECARD])
        fcntl.ioctl(self.wdt_hdlr, WDIOC_SETOPTIONS, req, False)

    def card_disable(self):
        # Turn off the watchdog timer
        req = array.array('h', [WDIOS_DISABLECARD])
        fcntl.ioctl(self.wdt_hdlr, WDIOC_SETOPTIONS, req, False)

    def keepalive(self):
        # Keep alive watchdog timer
        fcntl.ioctl(self.wdt_hdlr, WDIOC_KEEPALIVE)

    def is_armed(self):
        return self.armed

    def get_remaining_time(self):
        if self.is_armed():
            req = array.array('I', [0])
            fcntl.ioctl(self.watchdog, WDIOC_GETTIMELEFT, req, True)
            rem = int(req[0])
            if rem < 0:
                return 0
            return rem
        return -1

    def set_timeout(self, seconds):
        # Set watchdog timer
        req = array.array('I', [seconds])
        fcntl.ioctl(self.wdt_hdlr, WDIOC_SETTIMEOUT, req, True)
        return int(req[0])

    def arm(self, seconds):
        err = WD_ERROR
        if seconds < 0 or seconds > WDT_MAX_TIMEOUT:
            return err

        if self.wdt_dev is None:
            return err
        
        if self.wdt_hdlr is None:
            #Disarmed reopen file to arm
            try:
                self.wdt_hdlr = os.open(self.wdt_dev, os.O_WRONLY)
                if self.wdt_hdlr is None:
                    return err
            except IOError:
                pass
        try:
            self.set_timeout(seconds)
            if self.armed:
                self.keepalive()
            else:
                self.armed = True
                self.card_enable()

            self.wdt_expire  = time.time() + (seconds/2)*2
        except IOError:
            pass

        return (seconds/2)*2

    def disarm(self):
        if self.wdt_hdlr is None:
            return False
        try:
            os.write(self.wdt_hdlr, b'V')
            self.card_disable()
            self.armed = False
            os.close(self.wdt_hdlr)
            return True
        except IOError:
            return False

    def __del__(self):
        self.disarm()


# w1 =  Watchdog()
# w1.is_armed()
# w1.arm(150)
# print("\nTime left : {}".format(w1.get_remaining_time()))
# w1.keepalive()
# w1.disarm()

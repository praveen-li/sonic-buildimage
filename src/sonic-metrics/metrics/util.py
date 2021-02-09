import subprocess
import shlex
import syslog
import os
import re

SYSLOG_IDENTIFIER = os.path.basename(__file__)

def run_command(command):
    """
    Utility function to run an shell command and return the output.
    :param command: Shell command string.
    :return: Output of the shell command.
    """
    process = subprocess.Popen(shlex.split(command), shell=False, stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output, error

def log_info(msg, also_print_to_console=False):
    syslog.openlog(SYSLOG_IDENTIFIER)
    syslog.syslog(syslog.LOG_INFO, msg)
    syslog.closelog()
    if also_print_to_console:
        print msg

def log_warning(msg, also_print_to_console=False):
    syslog.openlog(SYSLOG_IDENTIFIER)
    syslog.syslog(syslog.LOG_WARNING, msg)
    syslog.closelog()

    if also_print_to_console:
        print msg

def log_error(msg, also_print_to_console=False):
    syslog.openlog(SYSLOG_IDENTIFIER)
    syslog.syslog(syslog.LOG_ERR, msg)
    syslog.closelog()
    if also_print_to_console:
        print msg


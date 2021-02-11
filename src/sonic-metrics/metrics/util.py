#!/usr/bin/python
try:
    import subprocess
    import shlex
    import syslog
    import os
    import re
    import yaml
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

SYSLOG_IDENTIFIER = os.path.basename(__file__)

#
# ====================== Constants =======================================
#

SONIC_VERSION_YAML_PATH = "/etc/sonic/sonic_version.yml"
VER_PATTERN = 'lnos_v(\d+)\.(\d+)\.(\d+)'

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


def get_sonic_version_info():
    """
    Utility function to get SONiC version and
    return the full version.
    :param command: SONIC_VERSION_YAML_PATH
    :return: string(version output)
    """
    if not os.path.isfile(SONIC_VERSION_YAML_PATH):
        return None

    data = {}
    with open(SONIC_VERSION_YAML_PATH) as stream:
        if yaml.__version__ >= "5.1":
            data = yaml.full_load(stream)
        else:
            data = yaml.load(stream)

    return data


def check_version():
    """
    Utility function to check SONiC version and
    return the release, major and minor version.
    :param command:
    :return: tuple(rel, major, minor)
    """
    version_info = get_sonic_version_info()
    if version_info:
        build_version = version_info['build_version']
        rel_var_regx = re.compile(VER_PATTERN)

        matches = rel_var_regx.match(build_version)
        if matches:
            rel, major, minor = matches.groups()
            return rel, major, minor

    return None, None, None

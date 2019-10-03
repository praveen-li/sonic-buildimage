import yang as ly
import logging
import argparse
import sys
import ijson
import json
#import sonic_yang as sy
from os import listdir
from os.path import isfile, join, splitext

#Globals vars
PASS = 0
FAIL = 1
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("YANG-TEST")
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

# Global functions
def printExceptionDetails():
    try:
        excType, excObj, traceBack = sys.exc_info()
        fileName = traceBack.tb_frame.f_code.co_filename
        lineNumber = traceBack.tb_lineno
        log.error(" Exception >{}< in {}:{}".format(excObj, fileName, lineNumber))
    except Exception as e:
        log.error(" Exception in printExceptionDetails")
    return

# class for YANG Model YangModelTesting
# Run function will run all the tests
# from a user given list.

class YangModelTesting:

    def __init__(self, tests, yangDir, jsonFile):
        self.tests = tests
        self.yangDir = yangDir
        self.jsonFile = jsonFile
        self.testNum = 1
        # other class vars
        # self.ctx
        return

    """
        load all YANG models before test run
    """
    def loadYangModel(self, yangDir):
        try:
            # get all files
            yangFiles = [f for f in listdir(yangDir) if isfile(join(yangDir, f))]
            # get all yang files
            yangFiles = [f for f in yangFiles if splitext(f)[-1].lower()==".yang"]
            yangFiles = [f.split('.')[0] for f in yangFiles]
            # load yang mdoules
            self.ctx = ly.Context(yangDir)
            log.debug(yangFiles)
            for f in yangFiles:
                # load a module
                log.debug(f)
                m = self.ctx.get_module(f)
                if m is not None:
                    log.error("Could not get module: {}".format(m.name()))
                else:
                    m = self.ctx.load_module(f)
                    if m is not None:
                        log.info("module: {} is loaded successfully".format(m.name()))
                    else:
                        return
        except Exception as e:
            printExceptionDetails()
            raise e
        return

    """
        Run all tests from list self.tests
    """
    def run(self):
        try:
            self.loadYangModel(self.yangDir)
            ret = 0
            for test in self.tests:
                func = "yangTest" + test;
                # Pass function name, needed to retrieve input Json Dictionary
                ret = ret + getattr(self, func)(func)
        except Exception as e:
            printExceptionDetails()
            raise e
        return ret

    """
        Get the JSON input based on func name
        and return jsonInput
    """
    def readJsonInput(self, func):
        try:
            # load test specific Dictionary, using Key = func
            # this is to avoid loading very large JSON in memory
            log.debug(" Read JSON Section: " + func)
            jInput = ""
            with open(self.jsonFile, 'rb') as f:
                jInst = ijson.items(f, func)
                for it in jInst:
                    jInput = jInput + json.dumps(it)
            log.debug(jInput)
        except Exception as e:
            printExceptionDetails()
        return jInput

    """
        Log the start of a test
    """
    def logStartTest(self, tStr):
        log.info("\n------------------- Test "+ str(self.testNum) +\
        ": " + tStr + "---------------------")
        self.testNum = self.testNum + 1
        return

    """
        Load Config Data and return Exception as String
    """
    def loadConfigData(self, jInput):
        s = ""
        try:
            node = self.ctx.parse_data_mem(jInput, ly.LYD_JSON, \
            ly.LYD_OPT_CONFIG | ly.LYD_OPT_STRICT)
        except Exception as e:
            s = str(e)
            log.debug(s)
        return s

    """
        Test 1: Configure Wrong family with ip-prefix for VLAN_Interface Table.
    """
    def yangTest1(self, func):
        try:
            tStr = " Configure Wrong family with ip-prefix for VLAN_Interface Table."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Must condition" in s and "not satisfied" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Test 2: Add dhcp_server which is not in correct ip-prefix format.
    """
    def yangTest2(self, func):
        try:
            tStr = " Add dhcp_server which is not in correct ip-prefix format."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Invalid value" in s and "dhcp_servers" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure a member port in VLAN_MEMBER table which does not exist.
    """
    def yangTest3(self, func):
        try:
            tStr = " Configure a member port in VLAN_MEMBER table which does not exist."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Leafref" in s and "non-existing" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure vlan-id in VLAN_MEMBER table which does not exist in VLAN  table.
    """
    def yangTest4(self, func):
        try:
            tStr = " Configure vlan-id in VLAN_MEMBER table which does not exist in VLAN  table."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Leafref" in s and "non-existing" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure wrong value for tagging_mode.
    """
    def yangTest5(self, func):
        try:
            tStr = " Configure wrong value for tagging_mode."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Invalid value" in s and "tagging_mode" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure empty string as ip-prefix in INTERFACE table.
    """
    def yangTest6(self, func):
        try:
            tStr = " Configure empty string as ip-prefix in INTERFACE table."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Invalid value" in s and "ip-prefix" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure undefined packet_action in ACL_RULE table.
    """
    def yangTest7(self, func):
        try:
            tStr = " Configure undefined packet_action in ACL_RULE table."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Invalid value" in s and "PACKET_ACTION" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure undefined acl_table_type in ACL_TABLE table.
    """
    def yangTest8(self, func):
        try:
            tStr = " Configure undefined acl_table_type in ACL_TABLE table."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Invalid value" in s and "type" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure non-existing ACL_TABLE in ACL_RULE.
    """
    def yangTest9(self, func):
        try:
            tStr = " Configure non-existing ACL_TABLE in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("Leafref" in s and "non-existing" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure IP_TYPE as ipv4any and SRC_IPV6 in ACL_RULE.
    """
    def yangTest10(self, func):
        try:
            tStr = " Configure IP_TYPE as ipv4any and SRC_IPV6 in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("When condition" in s and "not satisfied" in s and "IP_TYPE" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure IP_TYPE as ARP and DST_IPV6 in ACL_RULE.
    """
    def yangTest11(self, func):
        try:
            tStr = " Configure IP_TYPE as ARP and DST_IPV6 in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("When condition" in s and "not satisfied" in s and "IP_TYPE" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure l4_src_port_range as 99999-99999 in ACL_RULE.
    """
    def yangTest12(self, func):
        try:
            tStr = " Configure l4_src_port_range as 99999-99999 in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("does not satisfy" in s and "pattern" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

    """
        Configure IP_TYPE as ARP and ICMPV6_CODE in ACL_RULE.
    """
    def yangTest13(self, func):
        try:
            tStr = " Configure IP_TYPE as ARP and ICMPV6_CODE in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("When condition" in s and "not satisfied" in s and "IP_TYPE" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL


    """
        Configure INNER_ETHER_TYPE as 0x080C in ACL_RULE.
    """
    def yangTest14(self, func):
        try:
            tStr = " Configure INNER_ETHER_TYPE as 0x080C in ACL_RULE."
            self.logStartTest(tStr)
            jInput = self.readJsonInput(func)
            # load the data, expect a exception with must condition failure
            s = self.loadConfigData(jInput)
            if ("does not satisfy" in s and "pattern" in s):
                log.info(tStr + " Passed\n")
                return PASS
        except Exception as e:
            printExceptionDetails()
        log.info(tStr + " Failed\n")
        return FAIL

# End of Class

"""
    Start Here
"""
def main():
    parser = argparse.ArgumentParser(description='Script to run YANG model tests',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog="""
Usage:
python yangModelTesting.py -h
""")
    parser.add_argument('-t', '--tests', type=str, \
    help='Tests to run, Format 1,2,3', required=True)
    parser.add_argument('-f', '--json-file', type=str, \
    help='JSON input for tests ', required=True)
    parser.add_argument('-y', '--yang-dir', type=str, \
    help='Path to YANG models', required=True)
    parser.add_argument('-v', '--verbose-level', type=str, \
    help='Verbose Level of Logs', choices=['INFO', 'DEBUG'])
    args = parser.parse_args()
    try:
        tests = args.tests
        jsonFile = args.json_file
        yangDir = args.yang_dir
        logLevel = args.verbose_level
        if logLevel == "DEBUG":
            log.setLevel(logging.DEBUG)
        # Make a list
        tests = tests.split(",")
        yTest = YangModelTesting(tests, yangDir, jsonFile)
        ret = yTest.run()
        if ret == 0:
            log.info("All Test Passed")
        sys.exit(ret)
    except Exception as e:
        printExceptionDetails()
        sys.exit(1)

    return
if __name__ == '__main__':
    main()

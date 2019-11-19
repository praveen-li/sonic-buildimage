# This script is used to

import yang as ly
import re
import pprint

from json import dump, load, dumps, loads
from xmltodict import parse
from os import listdir, walk, path
from os.path import isfile, join, splitext

# Read given JSON file
def readJsonFile(fileName):
    #print(fileName)
    try:
        with open(fileName) as f:
            result = load(f)
    except Exception as e:
        raise Exception(e)

    return result

prt = pprint.PrettyPrinter(indent=4)
def prtprint(obj):
    prt.pprint(obj)
    return

class sonic_yang:

    def __init__(self, yangDir):
        self.yangDir = yangDir
        self.ctx = None;
        self.yangFiles = list()
        self.confDbYangMap = dict()
        self.yJson = list()
        self.jIn = None
        self.xlateJson = dict()
        self.revXlateJson = dict()

        return

    """
        load all YANG models before test run
    """
    def loadYangModel(self):

        yangDir = self.yangDir
        # get all files
        yangFiles = [f for f in listdir(yangDir) if isfile(join(yangDir, f))]
        # get all yang files
        yangFiles = [f for f in yangFiles if splitext(f)[-1].lower()==".yang"]
        yangFiles = [f.split('.')[0] for f in yangFiles]
        # load yang mdoules
        self.ctx = ly.Context(yangDir)
        self.yangFiles = yangFiles
        print(yangFiles)
        for f in yangFiles:
            # load a module
            m = self.ctx.get_module(f)
            if m is not None:
                print("module already exist: {}".format(m.name()))
            else:
                m = self.ctx.load_module(f)
                if m is not None:
                    print("module: {} is loaded successfully".format(m.name()))
                else:
                    print("module not loaded correctly: {}".format(m.name()))
                    return

        return

    """
        load JSON schema format from yang models
    """
    def loadJsonYangModel(self):

        for f in self.yangFiles:
            m = self.ctx.get_module(f)
            if m is not None:
                xml = m.print_mem(ly.LYD_JSON, ly.LYP_FORMAT)
                self.yJson.append(parse(xml))

        return

    """
        Create a map from config DB tables to
    """
    def createDBTableToModuleMap(self):

        for j in self.yJson:
            # get module name
            moduleName = j['module']['@name']
            if "sonic-head" in moduleName or "sonic-common" in moduleName:
                continue;
            # get all top level container
            topLevelContainer = j['module']['container']
            if topLevelContainer is None:
                raise Exception("topLevelContainer not found")

            assert topLevelContainer['@name'] == moduleName

            container = topLevelContainer['container']
            # container is a list
            if isinstance(container, list):
                for c in container:
                    self.confDbYangMap[c['@name']] = {
                        "module":moduleName,
                        "topLevelContainer": topLevelContainer['@name'],
                        "container": c
                        }
            # container is a dict
            else:
                self.confDbYangMap[container['@name']] = {
                    "module":moduleName,
                    "topLevelContainer": topLevelContainer['@name'],
                    "container": container
                    }
        return

    """
    Extract keys from table entry in Config DB and return in a dict
    """
    def extractKey(self, tableKey, regex):

        # get the keys from regex of key extractor
        keyList = re.findall(r'<(.*?)>', regex)
        # create a regex to get values from tableKey
        # and change separator to text in regexV
        regexV = re.sub('<.*?>', '(.*?)', regex)
        regexV = re.sub('\|', '\\|', regexV)
        # get the value groups
        value = re.match(r'^'+regexV+'$', tableKey)
        # create the keyDict
        i = 1
        keyDict = dict()
        for k in keyList:
            if value.group(i):
                keyDict[k] = value.group(i)
            else:
                raise Exception("Value not found for {} in {}".format(k, tableKey))
            i = i + 1

        return keyDict

    """
        Fill the dict based on leaf as a list or dict
        @model yang model object
    """
    def fillLeafDict(self, leafs, leafDict, isleafList=False):

        if leafs == None:
            return

        # fill default values
        def fillSteps(leaf):
            leaf['__isleafList'] = isleafList
            leafDict[leaf['@name']] = leaf
            return

        if isinstance(leafs, list):
            for leaf in leafs:
                #print("{}:{}".format(leaf['@name'], leaf))
                fillSteps(leaf)
        else:
            #print("{}:{}".format(leaf['@name'], leaf))
            fillSteps(leafs)

        return

    """
    create a dict to map each key under primary key with a dict yang model.
    This is done to improve performance of mapping from values of TABLEs in
    config DB to leaf in YANG LIST.
    """
    def createLeafDict(self, model):

        leafDict = dict()
        #Iterate over leaf, choices and leaf-list.
        self.fillLeafDict(model.get('leaf'), leafDict)

        #choices, this is tricky, since leafs are under cases in tree.
        choices = model.get('choice')
        if choices:
            for choice in choices:
                cases = choice['case']
                for case in cases:
                    self.fillLeafDict(case.get('leaf'), leafDict)

        # leaf-lists
        self.fillLeafDict(model.get('leaf-list'), leafDict, True)

        return leafDict

    """
    Convert a string from Config DB value to Yang Value based on type of the
    key in Yang model.
    @model : A List of Leafs in Yang model list
    """
    def findYangTypedValue(self, key, value, leafDict):

        # convert config DB string to yang Type
        def yangConvert(val):
            # find type of this key from yang leaf
            type = leafDict[key]['type']['@name']
            # TODO: vlanid will be fixed with leafref
            if 'uint' in type or 'vlanid' == key :
                vValue = int(val, 10)
            # TODO: find type of leafref from schema node
            elif 'leafref' in type:
                vValue = val
            #TODO: find type in sonic-head, as of now, all are enumeration
            elif 'head:' in type:
                vValue = val
            else:
                vValue = val
            return vValue

        # if it is a leaf-list do it for each element
        if leafDict[key]['__isleafList']:
            vValue = list()
            for v in value:
                vValue.append(yangConvert(v))
        else:
            vValue = yangConvert(value)

        return vValue

    """
    Xlate a list
    This function will xlate from a dict in config DB to a Yang JSON list
    using yang model. Output will be go in self.xlateJson
    """
    def xlateList(self, model, yang, config, table):

        # TODO: define a keyExt dict as of now, but we should be able to extract
        # this from YANG model extentions.
        keyExt = {
            "VLAN_INTERFACE": "Vlan<vlan>|<ip-prefix>",
            "ACL_RULE": "<ACL_TABLE_NAME>|<RULE_NAME>",
            "VLAN": "Vlan<vlan>",
            "VLAN_MEMBER": "Vlan<vlan>|<port>",
            "ACL_TABLE": "<ACL_TABLE_NAME>",
            "INTERFACE": "<interface>|<ip-prefix>",
            "PORT": "<port_name>"
        }
        #print(table)
        #create a dict to map each key under primary key with a dict yang model.
        #This is done to improve performance of mapping from values of TABLEs in
        #config DB to leaf in YANG LIST.

        leafDict = self.createLeafDict(model)
        #prtprint(leafDict)

        # Find and extracts key from each dict in config
        for pkey in config:
            #print(items)
            keyDict = self.extractKey(pkey, keyExt[table])
            # fill rest of the values in keyDict
            for vKey in config[pkey]:
                keyDict[vKey] = self.findYangTypedValue(vKey, \
                                    config[pkey][vKey], leafDict)
            #print(keyDict)
            yang.append(keyDict)

        return

    """
    Xlate a container
    This function will xlate from a dict in config DB to a Yang JSON container_of
    using yang model. Output will be go in self.xlateJson
    """
    def xlateContainer(self, model, yang, config, table):

        # if container contains single list with containerName_LIST and
        # config is not empty then xLate the list
        clist = model.get('list')
        if clist and isinstance(clist, dict) and \
           clist['@name'] == model['@name']+"_LIST" and bool(config):
                #print(clist['@name'])
                yang[clist['@name']] = list()
                self.xlateList(model['list'], yang[clist['@name']], \
                               config, table)
                #print(yang[clist['@name']])

        # TODO: Handle mupltiple list and rest of the field in Container.
        # We do not have any such instance in Yang model today.

        return

    """
        xlate ConfigDB json to Yang json
    """
    def xlateConfigDBtoYang(self):

        yangJ = self.xlateJson
        # find top level container for each table ,
        # and run the xlate_container
        for table in self.jIn.keys():
            print("xlate " + table)
            cmap = self.confDbYangMap[table]
            # create top level containers
            key = cmap['module']+":"+cmap['topLevelContainer']
            subkey = cmap['topLevelContainer']+":"+cmap['container']['@name']
            # Add new top level container for first table in this container
            yangJ[key] = dict() if yangJ.get(key) is None else yangJ[key]
            yangJ[key][subkey] = dict()
            #print(key + "--" + subkey)
            #print(yJson)
            self.xlateContainer(cmap['container'], yangJ[key][subkey], \
                                self.jIn[table], table)
            #print(yJson)

        return

    """
        Read config file and crop it as per yang models
    """
    def xlateConfigDB(self, xlateFile=None):

        # xlation is written in self.xlateJson
        self.xlateConfigDBtoYang()

        if xlateFile:
            with open(xlateFile, 'w') as f:
                dump(self.xlateJson, f, indent=4)

        return

    """
        Read config file and crop it as per yang models
    """
    def cropConfigDB(self, croppedFile=None):

        for table in self.jIn.keys():
            if table not in self.confDbYangMap:
                del self.jIn[table]

        if croppedFile:
            with open(croppedFile, 'w') as f:
                dump(self.jIn, f, indent=4)

        return

    """
        Load Config File
    """
    def loadConfig(self, configFile=None):

        if configFile:
            self.jIn = readJsonFile(configFile)
        else:
            # read from config DB
            pass

        return

    """
    create config DB table key from entry in yang JSON
    """
    def createKey(self, entry, regex):

        keyDict = dict()
        keyV = regex
        # get the keys from regex of key extractor
        keyList = re.findall(r'<(.*?)>', regex)
        for key in keyList:
            val = entry.get(key)
            if val:
                #print("pair: {} {}".format(key, val))
                keyDict[key] = sval = str(val)
                keyV = re.sub(r'<'+key+'>', sval, keyV)
                #print("VAL: {} {}".format(regex, keyV))
            else:
                raise Exception("key {} not found in entry".format(key))
        #print("kDict {}".format(keyDict))
        return keyV, keyDict

    """
    Convert a string from Config DB value to Yang Value based on type of the
    key in Yang model.
    @model : A List of Leafs in Yang model list
    """
    def revFindYangTypedValue(self, key, value, leafDict):

        # convert yang Type to config DB string
        def revYangConvert(val):
            # config DB has only strings, thank god for that :)
            return str(val)

        # if it is a leaf-list do it for each element
        if leafDict[key]['__isleafList']:
            vValue = list()
            for v in value:
                vValue.append(revYangConvert(v))
        else:
            vValue = revYangConvert(value)

        return vValue


    """
    Rev xlate from <TABLE>_LIST to table in config DB
    """
    def revXlateList(self, model, yang, config, table):

        # TODO: define a keyExt dict as of now, but we should be able to
        # extract this from YANG model extentions.
        keyExt = {
            "VLAN_INTERFACE": "Vlan<vlan>|<ip-prefix>",
            "ACL_RULE": "<ACL_TABLE_NAME>|<RULE_NAME>",
            "VLAN": "Vlan<vlan>",
            "VLAN_MEMBER": "Vlan<vlan>|<port>",
            "ACL_TABLE": "<ACL_TABLE_NAME>",
            "INTERFACE": "<interface>|<ip-prefix>",
            "PORT": "<port_name>"
        }

        # create a dict to map each key under primary key with a dict yang model.
        # This is done to improve performance of mapping from values of TABLEs in
        # config DB to leaf in YANG LIST.
        leafDict = self.createLeafDict(model)

        # list with name <TABLE>_LIST should be removed,
        # right now we have only this instance of LIST
        if model['@name'] == table + "_LIST":
            for entry in yang:
                # create key of config DB table
                pkey, pkeydict = self.createKey(entry, keyExt[table])
                config[pkey]= dict()
                # fill rest of the entries
                for key in entry:
                    if key not in pkeydict:
                        config[pkey][key] = self.revFindYangTypedValue(key, \
                            entry[key], leafDict)

        return

    """
    Rev xlate from yang container to table in config DB
    """
    def revXlateContainer(self, model, yang, config, table):

        # Note: right now containers has only LISTs.
        # IF container has only one list
        if isinstance(model['list'], dict):
            modelList = model['list']
            # Pass matching list from Yang Json
            self.revXlateList(modelList, yang[modelList['@name']], config, table)
        else:
            # TODO: Container[TABLE] contains multiple lists. [Test Pending]
            # No instance now.
            for modelList in model['list']:
                self.revXlateList(modelList, yang[modelList['@name']], config, table)

        return

    """
        rev xlate ConfigDB json to Yang json
    """
    def revXlateYangtoConfigDB(self):

        yangJ = self.xlateJson
        cDbJson = self.revXlateJson

        # find table in config DB, use name as a KEY
        for module_top in yangJ.keys():
            # module _top will be of from module:top
            for container in yangJ[module_top].keys():
                table = container.split(':')[1]
                print("revXlate " + table)
                cmap = self.confDbYangMap[table]
                cDbJson[table] = dict()
                #print(key + "--" + subkey)
                self.revXlateContainer(cmap['container'], yangJ[module_top][container], \
                    cDbJson[table], table)

        return

    """
        Reverse Translate tp config DB
    """
    def revXlateConfigDB(self, revXlateFile=None):

        # xlation is written in self.xlateJson
        self.revXlateYangtoConfigDB()

        if revXlateFile:
            with open(revXlateFile, 'w') as f:
                dump(self.revXlateJson, f, indent=4)

        return

# end of class


def test_xlate_rev_xlate():
    configFile = "sample_config_db.json"
    croppedFile = "cropped_" + configFile
    xlateFile = "xlate_" + configFile
    revXlateFile = "rev_" + configFile

    # load yang models
    sy = sonic_yang("../../../yang-models")
    # load yang models
    sy.loadYangModel()
    # create json for yang models [this is yang models in json format]
    sy.loadJsonYangModel()
    # create a mapping bw DB table and yang model containers
    sy.createDBTableToModuleMap()
    # load config from config_db.json or from config DB
    sy.loadConfig(configFile)
    # crop the config as per yang models
    sy.cropConfigDB(croppedFile)
    # xlate the config as per yang models
    sy.xlateConfigDB(xlateFile)
    # reverse xlate the config
    sy.revXlateConfigDB(revXlateFile)
    # compare cropped config and rex xlated config

    if sy.jIn == sy.revXlateJson:
        print("Xlate and Rev Xlate Passed")
    else:
        print("Xlate and Rev Xlate failed")
        from jsondiff import diff
        prtprint(diff(sy.jIn, sy.revXlateJson, syntax='symmetric'))

    return


def main():
    # test xlate and rev xlate
    test_xlate_rev_xlate()
    return

if __name__ == "__main__":
    main()

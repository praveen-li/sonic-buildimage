# This script is used to

import yang as ly
import re
import pprint

from json import dump, load, dumps, loads
from xmltodict import parse
from os import listdir, walk, path
from os.path import isfile, join, splitext
from glob import glob

prt = pprint.PrettyPrinter(indent=4)
def prtprint(obj):
    prt.pprint(obj)
    return

# class sonic_yang methods

"""
load_data: load a Yang data in json
input:    data
returns:  True - success   False - failed
"""
def load_data(self, configdbJson):

   try:
      self.jIn = configdbJson
      # reset xlate
      self.xlateJson = dict()
      # self.jIn will be cropped
      self.cropConfigDB("cropped.json")
      # xlated result will be in self.xlateJson
      self.xlateConfigDB("xlateYang.json")
      #print(self.xlateJson)
      self.root = self.ctx.parse_data_mem(dumps(self.xlateJson), \
                    ly.LYD_JSON, ly.LYD_OPT_CONFIG|ly.LYD_OPT_STRICT)

   except Exception as e:
       self.root = None
       print("Data Loading Failed")
       raise e

   return True

"""
Get data from Data tree, data tree will be assigned in self.xlateJson
"""
def get_data(self):

    try:
        self.xlateJson = self.print_data_mem('JSON')
        # reset reverse xlate
        self.revXlateJson = dict()
        # print_data_mem returns in string format
        self.xlateJson = loads(self.xlateJson)
        # result will be stored self.revXlateJson
        self.revXlateConfigDB("revXlateYang.json")

    except Exception as e:
        print("Get Data Tree Failed")
        raise e

    return self.revXlateJson

"""
Delete a node from data tree, if this is LEAF and KEY Delete the Parent
"""
def delete_node(self, xpath):

    node = self.find_data_node(xpath)
    # check for a leaf if it is a key. If yes delete the parent
    snode = node.schema(); LYS_LEAF = 4

    if (snode.nodetype() == LYS_LEAF):
        leaf = ly.Schema_Node_Leaf(snode)
        if leaf.is_key():
            print("Key: {}".format(xpath))
            # try to delete parent
            nodeP = self.find_parent_node(xpath)
            xpathP = nodeP.path()
            print("Del Parent {}".format(xpathP))
            return self._delete_node(xpath=xpathP, node=nodeP)
    else:
        print("Del: {}".format(xpath))
        return self._delete_node(xpath=xpath, node=node)

    return True

"""
load all YANG models before test run
"""
def loadYangModel(self):

    try:
        yangDir = self.yang_dir
        self.yangFiles = glob(yangDir +"/*.yang")
        for file in self.yangFiles:
            if (self.load_schema_module(file) == False):
                return False

        # keep only modules name in self.yangFiles
        self.yangFiles = [f.split('/')[-1] for f in self.yangFiles]
        self.yangFiles = [f.split('.')[0] for f in self.yangFiles]
        print(self.yangFiles)

        # load json for each yang model
        self.loadJsonYangModel()
        # create a map from config DB table to yang container
        self.createDBTableToModuleMap()

    except Exception as e:
        print("Yang Models Load failed")
        raise e

    return True

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
Get module, topLevelContainer and json container for a config DB table
"""
def get_module_top_container(self, table):
    cmap = self.confDbYangMap
    m = cmap[table]['module']
    t = cmap[table]['topLevelContainer']
    c = cmap[table]['container']
    return m, t, c

"""
Find a list in YANG Container
c = container
l = list name
return: list if found else None
"""
def findYangList(self, container, listName):

    if isinstance(container['list'], dict):
        clist = container['list']
        if clist['@name'] == listName:
            return clist

    elif isinstance(container['list'], list):
        clist = [l for l in container['list'] if l['@name'] == listName]
        return clist[0]

    return None

"""
Find xpath of the PORT Leaf in PORT container/list. Xpath of Leaf is needed,
because only leaf can have leafrefs depend on them.
"""
def findXpathPortLeaf(self, portName):

    try:
        table = "PORT"
        xpath = self.findXpathPort(portName)
        module, topc, container = self.get_module_top_container(table)
        list = self.findYangList(container, table+"_LIST")
        xpath = xpath + "/" + list['key']['@value'].split()[0]
    except Exception as e:
        print("find xpath of port Leaf failed")
        raise e

    return xpath


"""
Find xpath of PORT
"""
def findXpathPort(self, portName):

    try:
        table = "PORT"
        module, topc, container = self.get_module_top_container(table)
        xpath = "/" + module + ":" + topc + "/" + table

        list = self.findYangList(container, table+"_LIST")
        xpath = self.findXpathList(xpath, list, [portName])
    except Exception as e:
        print("find xpath of port failed")
        raise e

    return xpath

"""
Find xpath of a YANG LIST from keys,
xpath: xpath till list
list: YANG List
keys: list of keys in YANG LIST
"""
def findXpathList(self, xpath, list, keys):

    try:
        # add list name in xpath
        xpath = xpath + "/" + list['@name']
        listKeys = list['key']['@value'].split()
        i = 0;
        for listKey in listKeys:
            xpath = xpath + '['+listKey+'=\''+keys[i]+'\']'
            i = i + 1
    except Exception as e:
        print("find xpath of list failed")
        raise e

    return xpath


"""
Create a map from config DB tables to container in yang model
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
                    "module" : moduleName,
                    "topLevelContainer": topLevelContainer['@name'],
                    "container": c
                    }
        # container is a dict
        else:
            self.confDbYangMap[container['@name']] = {
                "module" : moduleName,
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
Fill the dict based on leaf as a list or dict @model yang model object
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
            # Few keys are already interger in configDB such as Priority and
            # speed.

            if isinstance(val, int):
                vValue = val
            else:
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
        "VLAN_INTERFACE": "<vlan_name>|<ip-prefix>",
        "ACL_RULE": "<ACL_TABLE_NAME>|<RULE_NAME>",
        "VLAN": "<vlan_name>",
        "VLAN_MEMBER": "<vlan_name>|<port>",
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
        try:
            keyDict = self.extractKey(pkey, keyExt[table])
            # fill rest of the values in keyDict
            for vKey in config[pkey]:
                keyDict[vKey] = self.findYangTypedValue(vKey, \
                                    config[pkey][vKey], leafDict)
        #print(keyDict)
            yang.append(keyDict)
        except Exception as e:
            print("Exception while Config DB --> YANG: pkey:{}, "\
            "vKey:{}, value: {}".format(pkey, vKey, config[pkey][vKey]))
            raise e

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
def xlateConfigDBtoYang(self, jIn, yangJ):

    # find top level container for each table ,
    # and run the xlate_container
    for table in jIn.keys():
        #print("xlate " + table)
        cmap = self.confDbYangMap[table]
        #print("cmap: {}".format(cmap))
        # create top level containers
        key = cmap['module']+":"+cmap['topLevelContainer']
        subkey = cmap['topLevelContainer']+":"+cmap['container']['@name']
        # Add new top level container for first table in this container
        yangJ[key] = dict() if yangJ.get(key) is None else yangJ[key]
        yangJ[key][subkey] = dict()
        #print(key + "--" + subkey)
        #print(yangJ)
        self.xlateContainer(cmap['container'], yangJ[key][subkey], \
                            jIn[table], table)
        #print(yJson)

    return

"""
Read config file and crop it as per yang models
"""
def xlateConfigDB(self, xlateFile=None):

    jIn= self.jIn
    yangJ = self.xlateJson
    # xlation is written in self.xlateJson
    self.xlateConfigDBtoYang(jIn, yangJ)

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
def loadConfig(self, jIn=None, configFile=None):

    if jIn:
        self.jIn=jIn
    elif configFile:
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
        # config DB has only strings, thank god for that :), wait not yet!!!
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
        "VLAN_INTERFACE": "<vlan_name>|<ip-prefix>",
        "ACL_RULE": "<ACL_TABLE_NAME>|<RULE_NAME>",
        "VLAN": "<vlan_name>",
        "VLAN_MEMBER": "<vlan_name>|<port>",
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
def revXlateYangtoConfigDB(self, yangJ, cDbJson):

    yangJ = self.xlateJson
    cDbJson = self.revXlateJson

    # find table in config DB, use name as a KEY
    for module_top in yangJ.keys():
        # module _top will be of from module:top
        for container in yangJ[module_top].keys():
            #table = container.split(':')[1]
            table = container
            #print("revXlate " + table)
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

    yangJ = self.xlateJson
    cDbJson = self.revXlateJson
    # xlation is written in self.xlateJson
    self.revXlateYangtoConfigDB(yangJ, cDbJson)

    if revXlateFile:
        with open(revXlateFile, 'w') as f:
            dump(self.revXlateJson, f, indent=4)

    return

######## end of class funtions

# Test functions
def test_xlate_rev_xlate():
    configFile = "sample_config_db.json"
    croppedFile = "cropped_" + configFile
    xlateFile = "xlate_" + configFile
    revXlateFile = "rev_" + configFile

    # load yang models
    sy = sonic_yang("../../../yang-models")
    # load yang models
    sy.loadYangModel()
    # create a mapping bw DB table and yang model containers
    sy.createDBTableToModuleMap()
    # load config from config_db.json or from config DB
    sy.loadConfig(jIn=readJsonFile(configFile))
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

# This script is used as extension of sonic_yang class. It has methods of
# class sonic_yang. A separate file is used to avoid a single large file.

import yang as ly
import re
import pprint

from json import dump, load, dumps, loads
from xmltodict import parse
from os import listdir, walk, path
from os.path import isfile, join, splitext
from glob import glob

# class sonic_yang methods

"""
load all YANG models, create JSON of yang models
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
        print('Loaded below Yang Models')
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

    try:
        for f in self.yangFiles:
            m = self.ctx.get_module(f)
            if m is not None:
                xml = m.print_mem(ly.LYD_JSON, ly.LYP_FORMAT)
                self.yJson.append(parse(xml))
    except Exception as e:
        print('JSON conversion for yang models failed')
        raise e

    return

"""
Create a map from config DB tables to container in yang model
This module name and topLevelContainer are fetched considering YANG models are
written using below Guidelines:
https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md.
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
Get module, topLevelContainer(TLC) and json container for a config DB table
"""
def get_module_TLC_container(self, table):
    cmap = self.confDbYangMap
    m = cmap[table]['module']
    t = cmap[table]['topLevelContainer']
    c = cmap[table]['container']
    return m, t, c

"""
Crop config as per yang models,
This Function crops from config only those TABLEs, for which yang models is
provided.
"""
def cropConfigDB(self, croppedFile=None, allowExtraTables=True):

    for table in self.jIn.keys():
        if table not in self.confDbYangMap:
            if allowExtraTables:
                del self.jIn[table]
            else:
                raise(Exception("No Yang Model Exist for {}".format(table)))

    if croppedFile:
        with open(croppedFile, 'w') as f:
            dump(self.jIn, f, indent=4)

    return

"""
Extract keys from table entry in Config DB and return in a dict

Input:
tableKey: Config DB Primary Key, Example tableKey = "Vlan111|2a04:5555:45:6709::1/64"
keys: key string from YANG list, i.e. 'vlan_name ip-prefix'.
regex: A regex to extract keys from tableKeys, good to have it as accurate as possible.

Return:
KeyDict = {"vlan_name": "Vlan111", "ip-prefix": "2a04:5555:45:6709::1/64"}
"""
def extractKey(self, tableKey, keys, regex):

    keyList = keys.split()
    #self.logInFile("extractKey {}".format(keyList))
    # get the value groups
    value = re.match(regex, tableKey)
    # create the keyDict
    i = 1
    keyDict = dict()
    for k in keyList:
        if value.group(i):
            keyDict[k] = value.group(i)
            # self.logInFile("extractKey {} {}".format(k, keyDict[k]))
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
        # Convert everything to string
        val = str(val)
        # find type of this key from yang leaf
        type = leafDict[key]['type']['@name']

        if 'uint' in type:
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
        "VLAN_INTERFACE_LIST": "^(Vlan[a-zA-Z0-9_-]+)$",
        "VLAN_LIST": "^(Vlan[a-zA-Z0-9_-]+)$",
        "VLAN_INTERFACE_IPPREFIX_LIST": "^(Vlan[a-zA-Z0-9_-]+)\|([a-fA-F0-9:./]+$)",
        "VLAN_MEMBER_LIST": "^(Vlan[a-zA-Z0-9-_]+)\|(Ethernet[0-9]+)$",
        "ACL_RULE_LIST": "^([a-zA-Z0-9_-]+)\|([a-zA-Z0-9_-]+)$",
        "ACL_TABLE_LIST": "^([a-zA-Z0-9-_]+)$",
        "INTERFACE_LIST": "^(Ethernet[0-9]+)$",
        "INTERFACE_IPPREFIX_LIST": "^(Ethernet[0-9]+)\|([a-fA-F0-9:./]+)$",
        "PORT_LIST": "^(Ethernet[0-9]+)$",
        "LOOPBACK_INTERFACE_LIST": "^([a-zA-Z0-9-_]+)$",
        "LOOPBACK_INTERFACE_IPPREFIX_LIST": "^([a-zA-Z0-9-_]+)\|([a-fA-F0-9:./]+)$",
    }
    #create a dict to map each key under primary key with a dict yang model.
    #This is done to improve performance of mapping from values of TABLEs in
    #config DB to leaf in YANG LIST.

    leafDict = self.createLeafDict(model)

    keyRegEx = keyExt[model['@name']]
    # get keys from YANG model list itself
    listKeys = model['key']['@value']

    for pkey in config.keys():
        try:
            vKey = None
            self.logInFile("xlateList Extract pkey {}".format(pkey))
            # Find and extracts key from each dict in config
            keyDict = self.extractKey(pkey, listKeys, keyRegEx)
            # fill rest of the values in keyDict
            for vKey in config[pkey]:
                self.logInFile("xlateList vkey {}".format(vKey))
                keyDict[vKey] = self.findYangTypedValue(vKey, \
                                    config[pkey][vKey], leafDict)
            yang.append(keyDict)
            # delete pkey from config, done to match one key with one list
            del config[pkey]

        except Exception as e:
            self.logInFile("xlateList Exception {}".format(e))
            self.logInFile("Exception while Config DB --> YANG: pkey:{}, "\
            "vKey:{}, value: {}".format(pkey, vKey, config[pkey].get(vKey)))
            # with multilist, we continue matching other keys.
            continue

    return

"""
Xlate a container
This function will xlate from a dict in config DB to a Yang JSON container
using yang model. Output will be stored in self.xlateJson
"""
def xlateContainer(self, model, yang, config, table):

    # To Handle multiple List, Make a copy of config, because we delete keys
    # from config after each match. This is done to match one pkey with one list.
    configC = config.copy()

    clist = model.get('list')
    # If single list exists in container,
    if clist and isinstance(clist, dict) and \
       clist['@name'] == model['@name']+"_LIST" and bool(configC):
            #print(clist['@name'])
            yang[clist['@name']] = list()
            self.logInFile("xlateContainer listD {}".format(clist['@name']))
            self.xlateList(clist, yang[clist['@name']], \
                           configC, table)
            # clean empty lists
            if len(yang[clist['@name']]) == 0:
                del yang[clist['@name']]
            #print(yang[clist['@name']])

    # If multi-list exists in container,
    elif clist and isinstance(clist, list) and bool(configC):
        for modelList in clist:
            yang[modelList['@name']] = list()
            self.logInFile("xlateContainer listL {}".format(modelList['@name']))
            self.xlateList(modelList, yang[modelList['@name']], configC, table)
            # clean empty lists
            if len(yang[modelList['@name']]) == 0:
                del yang[modelList['@name']]

    if len(configC):
        raise(Exception("All Keys are not parsed in {}".format(table)))

    return

"""
xlate ConfigDB json to Yang json
"""
def xlateConfigDBtoYang(self, jIn, yangJ):

    # find top level container for each table, and run the xlate_container.
    for table in jIn.keys():
        cmap = self.confDbYangMap[table]
        # create top level containers
        key = cmap['module']+":"+cmap['topLevelContainer']
        subkey = cmap['topLevelContainer']+":"+cmap['container']['@name']
        # Add new top level container for first table in this container
        yangJ[key] = dict() if yangJ.get(key) is None else yangJ[key]
        yangJ[key][subkey] = dict()
        self.logInFile("xlateConfigDBtoYang {}:{}".format(key, subkey))
        self.xlateContainer(cmap['container'], yangJ[key][subkey], \
                            jIn[table], table)

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
        "VLAN_INTERFACE_IPPREFIX_LIST": "<vlan_name>|<ip-prefix>",
        "VLAN_INTERFACE_LIST": "<vlan_name>",
        "VLAN_MEMBER_LIST": "<vlan_name>|<port>",
        "VLAN_LIST": "<vlan_name>",
        "ACL_RULE_LIST": "<ACL_TABLE_NAME>|<RULE_NAME>",
        "ACL_TABLE_LIST": "<ACL_TABLE_NAME>",
        "INTERFACE_LIST": "<port_name>",
        "INTERFACE_IPPREFIX_LIST": "<port_name>|<ip-prefix>",
        "LOOPBACK_INTERFACE_LIST": "<loopback_interface_name>",
        "LOOPBACK_INTERFACE_IPPREFIX_LIST": "<loopback_interface_name>|<ip-prefix>",
        "PORT_LIST": "<port_name>"

    }

    keyRegEx = keyExt[model['@name']]
    # create a dict to map each key under primary key with a dict yang model.
    # This is done to improve performance of mapping from values of TABLEs in
    # config DB to leaf in YANG LIST.
    leafDict = self.createLeafDict(model)

    # list with name <NAME>_LIST should be removed,
    if "_LIST" in model['@name']:
        for entry in yang:
            # create key of config DB table
            pkey, pkeydict = self.createKey(entry, keyRegEx)
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

    elif isinstance(model['list'], list):
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
        module, topc, container = self.get_module_TLC_container(table)
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
        module, topc, container = self.get_module_TLC_container(table)
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
load_data: load Config DB, crop, xlate and create data tree from it.
input:    data
returns:  True - success   False - failed
"""
def load_data(self, configdbJson, allowExtraTables=True):

   try:
      self.jIn = configdbJson
      # reset xlate
      self.xlateJson = dict()
      # self.jIn will be cropped
      self.cropConfigDB(allowExtraTables=allowExtraTables)
      # xlated result will be in self.xlateJson
      self.xlateConfigDB()
      #print(self.xlateJson)
      self.logInFile("Try to load Data in the tree")
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
        self.xlateJson = loads(self.print_data_mem('JSON'))
        # reset reverse xlate
        self.revXlateJson = dict()
        # result will be stored self.revXlateJson
        self.revXlateConfigDB()

    except Exception as e:
        print("Get Data Tree Failed")
        raise e

    return self.revXlateJson

"""
Delete a node from data tree, if this is LEAF and KEY Delete the Parent
"""
def delete_node(self, xpath):

    # These MACROS used only here, can we get it from Libyang Header ?
    try:
        LYS_LEAF = 4
        node = self.find_data_node(xpath)
        if node is None:
            raise('Node {} not found'.format(xpath))

        snode = node.schema()
        # check for a leaf if it is a key. If yes delete the parent
        if (snode.nodetype() == LYS_LEAF):
            leaf = ly.Schema_Node_Leaf(snode)
            if leaf.is_key():
                # try to delete parent
                nodeP = self.find_parent_node(xpath)
                xpathP = nodeP.path()
                if self._delete_node(xpath=xpathP, node=nodeP) == False:
                    raise('_delete_node failed')
                else:
                    return True

        # delete non key element
        if self._delete_node(xpath=xpath, node=node) == False:
            raise('_delete_node failed')
    except Exception as e:
        print(e)
        raise('Failed to delete node {}'.format(xpath))

    return True

# End of class sonic_yang
import yang as ly
import sys
import json
import glob

"""
Yang schema and data tree python APIs based on libyang python
"""
class sonic_yang:
    def __init__(self, yang_dir):
        self.yang_dir = yang_dir
        self.ctx = None
        self.module = None
        self.root = None
        # yang model files, need to map it to module
        self.yangFiles = list()
        # map from TABLE in config DB to container and module
        self.confDbYangMap = dict()
        # JSON format of yang model [similar to pyang conversion]
        self.yJson = list()
        # config DB json input, will be cropped as yang models
        self.jIn = None
        # YANG JSON, this is traslated from config DB json
        self.xlateJson = dict()
        # reverse translation from yang JSON, == config db json
        self.revXlateJson = dict()

        try:
            self.ctx = ly.Context(yang_dir)
        except Exception as e:
            print(e)

    from _sonic_yang_ext import *

    """
    load_schema_module(): load a Yang model file
    input:    yang_file - full path of a Yang model file
    returns:  True - success   False - failed
    """
    def load_schema_module(self, yang_file):
        try:
            self.ctx.parse_module_path(yang_file, ly.LYS_IN_YANG)
        except Exception as e:
            print(e)
            return False
        return True

    """
    load_schema_module_list(): load all Yang model files in the list
    input:    yang_files - a list of Yang model file full path
    returns:  True - success   False - failed
    """
    def load_schema_module_list(self, yang_files):
        for file in yang_files:
            if (self.load_schema_module(file) == False):
                return False
        return True

    """
    load_schema_modules(): load all Yang model files in the directory
    input:    yang_dir - the directory of the yang model files to be loaded
    returns:  True - success   False - failed
    """
    def load_schema_modules(self, yang_dir):
        py = glob.glob(yang_dir+"/*.yang")
        for file in py:
            if (self.load_schema_module(file) == False):
                return False
        return True

    """
    load_schema_modules_ctx(): load all Yang model files in the directory to context: ctx
    input:    yang_dir,  context
    returns:  context
    """
    def load_schema_modules_ctx(self, yang_dir):
        ctx = self.ctx
        py = glob.glob(yang_dir+"/*.yang")
        for file in py:
            ctx.parse_module_path(str(file), ly.LYS_IN_YANG)

        return ctx

    """
    load_data_file(): load a Yang data json file
    input:    data_file - the full path of the yang json data file to be loaded
    returns:  True - success   False - failed
    """
    def load_data_file(self, data_file):
       node = None
       try:
            node = self.ctx.parse_data_path(data_file, ly.LYD_JSON, ly.LYD_OPT_CONFIG | ly.LYD_OPT_STRICT)
       except Exception as e:
            print(e)
            return False
       self.root = node
       return True

    """
    get module name from xpath
    input:    xpath
    returns:  module name
    """
    def get_module_name(self, xpath):
        module_name = xpath.split(':')[0].strip('/')
        return module_name

    """
    get_module(): get module object from Yang module name
    input:   yang module name
    returns: Schema_Node object
    """
    def get_module(self, module_name):
        mod = self.ctx.get_module(module_name)
        return mod

    """
    load_data_model(): load both Yang module file and data json file
    input:   yang directory, yang file and data file
    returns: (context, root)
    """
    def load_data_model (self, yang_dir, yang_file, data_file, output):
        if (self.ctx is None):
            self.ctx = ly.Context(yang_dir)

        if self.module is  None:
            module = self.ctx.load_module(yang_file)
            self.module = module

        try:
            node = self.ctx.parse_data_path(data_file, ly.LYD_JSON, ly.LYD_OPT_CONFIG | ly.LYD_OPT_STRICT)
        except Exception as e:
            node = None
            print(e)

        self.root = node
        return (self.ctx, node)

    """
    print_data_mem():  print the data tree
    input:  option:  "JSON" or "XML"
    """
    def print_data_mem (self, option):
        if (option == "JSON"):
            mem = self.root.print_mem(ly.LYD_JSON, ly.LYP_WITHSIBLINGS | ly.LYP_FORMAT)
        else:
            mem = self.root.print_mem(ly.LYD_XML, ly.LYP_WITHSIBLINGS | ly.LYP_FORMAT)

        #print("======================= print data =================")
        #print(mem)
        return mem

    """
    save_data_file_json(): save the data tree in memory into json file
    input: outfile - full path of the file to save the data tree to
    """
    def save_data_file_json(self, outfile):
        mem = self.root.print_mem(ly.LYD_JSON, ly.LYP_FORMAT)
        with open(outfile, 'w') as out:
            json.dump(mem, out, indent=4)

    """
    get_module_tree(): get yang module tree in JSON or XMAL format
    input:   module name
    returns: JSON or XML format of the input yang module schema tree
    """
    def get_module_tree(self, module_name, format):
        result = None
        module = self.ctx.get_module(str(module_name))
        if (module is not None):
            if (format == "XML"):
                #libyang error with format
                result = module.print_mem(ly.LYD_JSON, ly.LYP_FORMAT)
            else:
                result = module.print_mem(ly.LYD_XML, ly.LYP_FORMAT)

        return result

    """
    validate_data(): validate data tree
    input:
           node:   root of the data tree
           ctx:    context
    returns:  True - success   False - failed
    """
    def validate_data (self, node, ctx):
        try:
            rc = node.validate(ly.LYD_OPT_CONFIG, ctx)
        except Exception as e:
            print(e)
            return False
        if (rc == 0):
            return True
        else:
            return False

    """
    validate_data_tree(): validate the data tree
    returns:  True - success   False - failed
    """
    def validate_data_tree (self):
        return self.validate_data(self.root, self.ctx)

    """
    find_parent_node():  find the parent node object
    input:    xpath of the node
    returns:  parent node
    """
    def find_parent_node (self, xpath):
        node = self.root
        if (node is None):
            print("data not loaded")
            return None
        #module_name = self.get_module_name(xpath)
        #self.ctx.load_module(module_name)
        node_set = self.root.find_path(xpath)
        if (node_set is not None):
            data_list = node_set.data()
            if (data_list == None):
                return None

            for elem in data_list:
                if (elem.path() == xpath):
                    if elem.parent() is not None:
                        return elem.parent()
                    else:
                        return None
        else:
            return None
        return node

    """
    get_parent_xpath():  find the parent node xpath
    input:    xpath of the node
    returns:  xpath of parent node
    """
    def get_parent_xpath (self, xpath):
        path=""
        node = self.find_parent_node(xpath)
        if (node is not None):
            path = node.path()

        return path

    """
    new_node(): create a new data node in the data tree
    input:
           xpath: xpath of the new node
           value: value of the new node
    reuturns:  new Data_Node object
    """
    def new_node(self, xpath, value):
        val = str(value)
        node = self.root.new_path(self.ctx, xpath, val, 0, 0)
        return node

    """
    find_data_node():  find the data node from xpath
    input:    xpath: xpath of the node
    returns   Data_Node object if found or None if not exist
    """
    def find_data_node(self, xpath):
        set = self.root.find_path(xpath)
        if (set is None):
            return None

        for node in set.data():
            if (xpath == node.path()):
                return node

        return None

    """
    find_schema_node(): find the schema node from xpath
    input:    xpath of the node
    returns:  Schema_Node oject or None if not found
    """
    def find_schema_node(self, xpath):
        module_name = self.get_module_name(xpath)
        self.ctx.load_module(module_name)

        set = self.root.find_path(xpath)
        if (set is None):
            print("set is None")
            return None

        for node in set.data():
            if (xpath == node.path()):
                return node.schema()

        return None

    """
    find_node_schema_xpath(): find the xpath of the schema node from xpath
    input:    xpath of the node
    returns:  xpath of the schema node
    """
    def find_node_schema_xpath(self, xpath):
        path = ""
        node = self.find_schema_node(xpath)
        if (node is not None):
            path = node.path()
        return path

    """
    add_node(): add a node to Yang schema or data tree
    input:    xpath and value of the node to be added
    returns:  True - success   False - failed
    """
    def add_node(self, xpath, value):
        node = self.new_node(xpath, value)
        if (node is not None):
            #find the node
            dnode = self.find_data_node(xpath)
            if (dnode is not None):
                return (dnode.path() == xpath)
            else:
                return False
        else:
            return False

    """
    merge_data(): merge a data file to the existing data tree
    input:    yang model directory and full path of the data json file to be merged
    returns:  True - success   False - failed
    """
    def merge_data(self, yang_dir, data_file):
        #load all yang models to ctx
        ctx = self.load_schema_modules_ctx(yang_dir)
        #source data node
        source_node = ctx.parse_data_path(str(data_file), ly.LYD_JSON, ly.LYD_OPT_CONFIG | ly.LYD_OPT_STRICT)
        #merge
        return self.root.merge(source_node, 0)

###Change in PLY CODE ###
    """
    _delete_node(): delete a node from the schema/data tree
    input:    xpath of the schema/data node
    returns:  True - success   False - failed
    """
    def _delete_node(self, xpath=None, node=None):
        if node is None:
            node = self.find_data_node(xpath)

        if (node):
            node.unlink()
            dnode = self.find_data_node(xpath)
            if (dnode is None):
                #deleted node not found
                return True
            else:
                #node still exists
                return False
        else:
            print("delete_node(): Did not found the node, xpath: " + xpath)
            return False

    """
    find_node_value():  find the value of a node from the schema/data tree
    input:    xpath of the schema/data node
    returns:  value string of the node
    """
    def find_node_value(self, xpath):
        output = ""
        node = self.find_data_node(xpath)
        if (node is not None):
             subtype = node.subtype()
             if (subtype is not None):
                  value = subtype.value_str()
                  return value
             else:
                 return output
        else:
            print("Node not found\n")
            return output

    """
    set the value of a node in the schema/data tree
    input:    xpath of the schema/data node
    returns:  True - success   False - failed
    """
    def set_dnode_value(self, xpath, value):
        try:
            node = self.root.new_path(self.ctx, xpath, str(value), ly.LYD_ANYDATA_STRING, ly.LYD_PATH_OPT_UPDATE)
        except Exception as e:
            print(e)
            return False

        return True

    """
    find_data_nodes(): find the set of nodes for the xpath
    input:    xpath of the schema/data node
    returns:  list of xpath of the dataset
    """
    def find_data_nodes(self, xpath):
        list = []
        node = self.root.child()
        node_set = node.find_path(xpath);

        if node_set is None:
            print("could not find data for xpath")
            sys.exit()

        for data_set in node_set.data():
            schema = data_set.schema()
            list.append(data_set.path())
        return list

    """
    find_schema_dependencies():  find the schema dependencies of the xpath
    input:    xpath of the schema node
    returns:  list of xpath of the dependencies
    """
    def find_schema_dependencies (self, xpath):
        ref_list = []
        node = self.root     #child()
        node_set = node.find_path(xpath)

        if node_set is None:
            print("could not find data for xpath")
            sys.exit()

        for data_set in node_set.data():
            data_list = data_set.child().tree_for()
            for elem in data_list:
                leaf = ly.Schema_Node_Leaf(elem.schema());
                if ("name" in elem.schema().name()):
                    backlinks = leaf.backlinks()
                    if backlinks.number() > 0:
                        for l_set in backlinks.schema():
                            ref_list.append(l_set.path())
        return ref_list

    """
    find_data_dependencies(): find the data dependencies of the xpath
    input:    xpath of the schema/data node
    returns:  list of xpath of the dependencies
    """
    def find_data_dependencies(self, xpath):
        ref_list = []
        node = self.root
        data_node = self.find_data_node(xpath)
        value = str(self.find_node_value(xpath))
        if data_node is None:
            raise("could not find the node for xpath")

        schema_node = ly.Schema_Node_Leaf(data_node.schema())
        backlinks = schema_node.backlinks()
        if backlinks.number() > 0:
            for link in backlinks.schema():
                node_set = node.find_path(link.path())
                for data_set in node_set.data():
                    schema = data_set.schema()
                    casted = data_set.subtype()
                    if value == casted.value_str():
                       ref_list.append(data_set.path())

        return ref_list

import sys
import os
import pytest
import sonic_yang as sy
import json
import glob
import logging
from ijson import items as ijson_itmes

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
sys.path.insert(0, modules_path)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("YANG-TEST")
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

class Test_SonicYang(object):
    # class vars

    @pytest.fixture(autouse=True, scope='class')
    def data(self):
        test_file = "/sonic/src/sonic-yang-mgmt/tests/libyang-python-tests/test_SonicYang.json"
        data = self.jsonTestParser(test_file)
        return data

    @pytest.fixture(autouse=True, scope='class')
    def yang_s(self, data):
        yang_dir = str(data['yang_dir'])
        yang_s = sy.sonic_yang(yang_dir)
        return yang_s

    def jsonTestParser(self, file):
        """
        Open the json test file
        """
        with open(file) as data_file:
            data = json.load(data_file)
        return data

    """
        Get the JSON input based on func name
        and return jsonInput
    """
    def readIjsonInput(self, yang_test_file, test):
        try:
            # load test specific Dictionary, using Key = func
            # this is to avoid loading very large JSON in memory
            print(" Read JSON Section: " + test)
            jInput = ""
            with open(yang_test_file, 'rb') as f:
                jInst = ijson_itmes(f, test)
                for it in jInst:
                    jInput = jInput + json.dumps(it)
        except Exception as e:
            print("Reading Ijson failed")
            raise(e)
        return jInput

    def setup_class(self):
        pass

    def load_yang_model_file(self, yang_s, yang_dir, yang_file, module_name):
        yfile = yang_dir + yang_file
        try:
	    yang_s.load_schema_module(str(yfile))
	except Exception as e:
            print(e)
            raise

    #test load and get yang module
    def test_load_yang_model_files(self, data, yang_s):
        yang_dir = data['yang_dir']
        for module in data['modules']:
            file = str(module['file'])
            module = str(module['module'])

            self.load_yang_model_file(yang_s, yang_dir, file, module)
            assert yang_s.get_module(module) is not None

    #test load non-exist yang module file
    def test_load_invalid_model_files(self, data, yang_s):
        yang_dir = data['yang_dir']
        file = "invalid.yang"
        module = "invalid"

        with pytest.raises(Exception):
             assert self.load_yang_model_file(yang_s, yang_dir, file, module)

    #test load yang modules in directory
    def test_load_yang_model_dir(self, data, yang_s):
        yang_dir = data['yang_dir']
        yang_s.load_schema_modules(str(yang_dir))

        for module_name in data['modules']:
            assert yang_s.get_module(str(module_name['module'])) is not None

    #test load yang modules and data files
    def test_load_yang_model_data(self, data, yang_s):
        yang_dir = str(data['yang_dir'])
        yang_files = glob.glob(yang_dir+"/*.yang")
        data_file = str(data['data_file'])
        data_merge_file = str(data['data_merge_file'])

        data_files = []
        data_files.append(data_file)
        data_files.append(data_merge_file)
	print(yang_files)
        yang_s.load_data_model(yang_dir, yang_files, data_files)

    #test load data file
    def test_load_data_file(self, data, yang_s):
        data_file = str(data['data_file'])
        yang_s.load_data_file(data_file)

    #test_validate_data_tree():
    def test_validate_data_tree(self, data, yang_s):
        yang_s.validate_data_tree()

    #test find node
    def test_find_node(self, data, yang_s):
        for node in data['data_nodes']:
            expected = node['valid']
            xpath = str(node['xpath'])
            dnode = yang_s.find_data_node(xpath)

            if(expected == "True"):
                 assert dnode is not None
                 assert dnode.path() == xpath
            else:
                 assert dnode is None

    #test add node
    def test_add_node(self, data, yang_s):
        for node in data['new_nodes']:
            xpath = str(node['xpath'])
            value = node['value']
            yang_s.add_node(xpath, str(value))

            node = yang_s.find_data_node(xpath)
            assert node is not None

    #test find node value
    def test_find_node_value(self, data, yang_s):
       for node in data['node_values']:
            xpath = str(node['xpath'])
            value = str(node['value'])
            print(xpath)
            print(value)
            val = yang_s.find_node_value(xpath)
            assert str(val) == str(value)

    #test delete data node
    def test_delete_node(self, data, yang_s):
        for node in data['delete_nodes']:
            xpath = str(node['xpath'])
            yang_s._delete_node(xpath)

    #test set node's value
    def test_set_datanode_value(self, data, yang_s):
        for node in data['set_nodes']:
            xpath = str(node['xpath'])
            value = node['value']
            yang_s.set_dnode_value(xpath, value)

            val = yang_s.find_node_value(xpath)
            assert str(val) == str(value)

    #test list of members
    def test_find_members(self, yang_s, data):
        for node in data['members']:
            members = node['members']
            xpath = str(node['xpath'])
            list = yang_s.find_data_nodes(xpath)
            assert list.sort() == members.sort()

    #get parent xpath
    def test_get_parent_xpath(self, yang_s, data):
        for node in data['parents']:
            xpath = str(node['xpath'])
            expected_xpath = str(node['parent'])
            path = yang_s.get_parent_xpath(xpath)
            assert path == expected_xpath

    #test find_node_schema_xpath
    def test_find_node_schema_xpath(self, yang_s, data):
        for node in data['schema_nodes']:
            xpath = str(node['xpath'])
            schema_xpath = str(node['value'])
            path = yang_s.find_node_schema_xpath(xpath)
            assert path == schema_xpath

    #test data dependencies
    def test_find_data_dependencies(self, yang_s, data):
        for node in data['dependencies']:
            xpath = str(node['xpath'])
            list = node['dependencies']
            depend = yang_s.find_data_dependencies(xpath)
            assert set(depend) == set(list)

    #test data dependencies
    def test_find_schema_dependencies(self, yang_s, data):
        for node in data['schema_dependencies']:
            xpath = str(node['xpath'])
            list = node['schema_dependencies']
            depend = yang_s.find_schema_dependencies(xpath)
            assert set(depend) == set(list)

    #test merge data tree
    def test_merge_data_tree(self, data, yang_s):
        data_merge_file = data['data_merge_file']
        yang_dir = str(data['yang_dir'])
        yang_s.merge_data(data_merge_file, yang_dir)
        #yang_s.root.print_mem(ly.LYD_JSON, ly.LYP_FORMAT)

    #test get module prefix
    def test_get_module_prefix(self, yang_s, data):
        for node in data['prefix']:
            xpath = str(node['module_name'])
            expected = node['module_prefix']
            prefix = yang_s.get_module_prefix(xpath)
            assert expected == prefix

    #test get data type
    def test_get_data_type(self, yang_s, data):
        for node in data['data_type']:
            xpath = str(node['xpath'])
            expected = node['data_type']
            expected_type = yang_s.str_to_type(expected)
            data_type = yang_s.get_data_type(xpath)
            assert expected_type == data_type

    def test_get_leafref_type(self, yang_s, data):
        for node in data['leafref_type']:
            xpath = str(node['xpath'])
            expected = node['data_type']
            expected_type = yang_s.str_to_type(expected)
            data_type = yang_s.get_leafref_type(xpath)
            assert expected_type == data_type

    def test_get_leafref_path(self, yang_s, data):
        for node in data['leafref_path']:
            xpath = str(node['xpath'])
            expected_path = node['leafref_path']
            path = yang_s.get_leafref_path(xpath)
            assert expected_path == path

    def test_get_leafref_type_schema(self, yang_s, data):
        for node in data['leafref_type_schema']:
            xpath = str(node['xpath'])
            expected = node['data_type']
            expected_type = yang_s.str_to_type(expected)
            data_type = yang_s.get_leafref_type_schema(xpath)
            assert expected_type == data_type

    def test_xlate_rev_xlate(self):
        # In this test, xlation and revXlation is tested with latest Sonic
        # YANG model.

        yang_dir = "/sonic/src/sonic-yang-models/yang-models/"
        yang_test_file = "/sonic/src/sonic-yang-models/tests/yang_model_tests/yangTest.json"
        jIn = self.readIjsonInput(yang_test_file, 'SAMPLE_CONFIG_DB_JSON')
        # load yang models
        syc = sy.sonic_yang(yang_dir)

        syc.loadYangModel()

        syc.load_data(json.loads(jIn))

        syc.get_data()

        if syc.jIn and syc.jIn == syc.revXlateJson:
            print("Xlate and Rev Xlate Passed")
        else:
            print("Xlate and Rev Xlate failed")
            # make it fail
            assert False == True

        return

    def teardown_class(self):
        pass

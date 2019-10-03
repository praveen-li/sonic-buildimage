import yang as ly
import sonic_yang as sy
import logging

from os import listdir
from os.path import isfile, join, splitext

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(":")
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())

def main():

    yangDir = "/sonic/src/sonic-yang-mgmt/models"
    yangDataInst = yangDir + "/sonic_config_data.json"
    
    # get all files
    yangFiles = [f for f in listdir(yangDir) if isfile(join(yangDir, f))]
    # get all yang files
    yangFiles = [f for f in yangFiles if splitext(f)[-1].lower()==".yang"]
    yangFiles = [f.split('.')[0] for f in yangFiles]

    # load yang mdoules
    ctx = ly.Context(yangDir)
    for f in yangFiles:
        # load a module m
        m = ctx.get_module(f)
        if m is not None:
            log.error(m.name())
        else:
            m = ctx.load_module(f)
            if m is not None:
                log.info("module: {} is loaded successfully".format(m.name()))

    try:
        root = ctx.parse_data_path(yangDataInst, ly.LYD_JSON, ly.LYD_OPT_CONFIG | ly.LYD_OPT_STRICT)
        
        if root:
            log.info("Tree DFS\n")
            p = root.print_mem(ly.LYD_JSON, ly.LYP_WITHSIBLINGS | ly.LYP_FORMAT)
            log.info("===================Data=================")
            log.info(p)

            sYangInst = sy.sonic_yang(yangDir)
            sYangInst.root = root
            sYangInst.validate_data_tree(root, ctx)

            xpath = "/sonic-port:PORT/PORT_LIST[port_name='Ethernet1']/port_name"
            #find_topo_sort_dependencies(sYangInst, xpath)
            refs = sYangInst.find_data_dependencies(xpath)
            printList(refs)

    except Exception as e:
        print(e)


def printList(l): # list l

    print("list: ")
    for item in l:
        print (item)
    
    return

if __name__ == '__main__':
    main()
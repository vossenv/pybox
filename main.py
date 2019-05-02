
import customlogging
import logging
import re
from subprocess import check_output



class Main:

    def __init__(self):
        customlogging.initLogger()
        self.logger = logging.getLogger("vbox")

    def run(self):
        x = str(check_output("vboxmanage list vms"))
        self.logger.info("Check!")

        vm_list = re.findall('(?<=")[^\\\\\n"]+?(?=")', x)


        print()




Main().run()
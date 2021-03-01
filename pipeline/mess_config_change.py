#
# Change the mcs_config.py file
#
from pipeline import util


class MessConfigChange:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def process(self):
        file_on_local_machine = "/home/clark/work/mcs/mcs-pipeline/pipeline/mcs_config.yaml"
        dir_on_remote_machine = "/home/ubuntu/mess_original_code/mess_final/"

        self.log.info(f"Copying mcs_config.yaml to machine {self.machine_dns}")

        return_code = util.copyFileToAWS(self.machine_dns, file_on_local_machine, self.log, dir_on_remote_machine)

        if return_code != 0:
            self.log.warn("Failed on starup step")
            return return_code

        return return_code

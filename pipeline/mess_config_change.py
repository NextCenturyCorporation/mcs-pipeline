#
# Change the mcs_config.yaml file
#
from pipeline import util

file_on_local = "/home/clark/work/mcs/mcs-pipeline/pipeline/mcs_config.yaml"
dir_on_remote = "/home/ubuntu/mess_original_code/mess_final/"


class MessConfigChange:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def process(self):
        self.log.info(f"Copying mcs_config.yaml to machine {self.machine_dns}")

        return_code = util.copyFileToAWS(self.machine_dns, file_on_local,
                                         self.log, dir_on_remote)

        if return_code != 0:
            self.log.warn("Failed on starup step")
            return return_code

        return return_code

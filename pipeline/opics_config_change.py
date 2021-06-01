#
# Change the mcs_config_opics_oracle.ini file
#
from pipeline import util

file_on_local = "configs/opics/mcs_config_opics_oracle.ini"
dir_on_remote = "/home/ubuntu/mcs_eval3-3.5.0/"


class OpicsConfigChange:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def process(self):
        self.log.info(f"Copying mcs_config_opics_oracle.ini to machine {self.machine_dns}")

        return_code = util.copy_file_to_aws(self.machine_dns, file_on_local,
                                            self.log, dir_on_remote)

        if return_code != 0:
            self.log.warn("Failed on startup step")
            return return_code

        return return_code

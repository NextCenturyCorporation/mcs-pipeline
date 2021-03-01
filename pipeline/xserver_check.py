#
# Check to make sure that the X server is properly running on a remote machine
#

from pipeline import util


class XServerCheck:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def process(self):
        self.log.info(f"Startup on machine {self.machine_dns}")

        # Clear out current tasks
        cmd = "ps auxwww | grep Xorg"
        return_code = util.shellRunCommand(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on starup step")
            return return_code

        return return_code

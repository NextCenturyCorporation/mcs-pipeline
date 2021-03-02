#
# Runs a trivial MCS program on the EC2 machine.
# If it does not run, check to make sure that the X server is properly
# running on a remote machine. Also check for timeout
#

from pipeline import util


class McsTestRunner:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def process(self):
        self.log.info(f"Startup on machine {self.machine_dns}")

        # Clear out current tasks
        cmd = "cd /home/ubuntu/ai2thor-docker && python3 mcs_test.py"
        return_code = util.shellRunCommand(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on starup step")
            return return_code

        return return_code

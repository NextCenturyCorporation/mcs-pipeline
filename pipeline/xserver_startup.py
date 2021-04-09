#
# Starts the XServer on the remote machine.  Since this takes a while, we start
# a new thread for it to run on, and return
#
import threading

from pipeline import util


class XServerStartup:

    def __init__(self, machine_dns, log):
        self.machine_dns = machine_dns
        self.log = log

    def start_x(self):
        '''Start the X server on the remote machine'''
        self.log.info(f"Startup on machine {self.machine_dns}")

        # Start x.  Put in quotes so all one command.
        cmd = "\"cd ~/mcs-pipeline/ && " + \
              "sudo python3 run_startx.py > /dev/null 2>&1 &\""
        return_code = util.shell_run_background_remote(self.machine_dns,
                                                       cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on starup step")
            return return_code

        return return_code

    def process(self):
        x = threading.Thread(target=self.start_x)
        x.start()

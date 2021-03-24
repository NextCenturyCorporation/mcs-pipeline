#
# Runs a single job on a single machine for OPICS
#
import os.path

from pipeline import util
from pipeline.singletask import SingleTask

# Where to find tasks.  Be sure to have '/' at end
all_tasks_dir = "/home/ubuntu/tasks/passive/all/"
current_tasks_dir = "/home/ubuntu/mcs_eval3-3.5.0/gravity_scenes/"

# The command that will be run to process a scene
run_command = "cd /home/ubuntu/mcs_eval3-3.5.0 && source activate mcs_opics && python3 eval.py --scenes gravity_scenes"


class OpicsSingleTask(SingleTask):

    def process(self):
        head, tail = os.path.split(self.json_file_name)
        self.log.info(f"---- Starting task with json file: {tail}")

        # Clear out current tasks
        cmd = "rm -f " + current_tasks_dir + "* || true"
        return_code = util.shell_run_command(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on rm old tasks step")
            return return_code

        # Copy the file from task dir to current task dir
        cmd = "cp " + all_tasks_dir + tail + " " + current_tasks_dir
        return_code = util.shell_run_command(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on cp new tasks step")
            return return_code

        # Run the command
        return_code = util.shell_run_command(self.machine_dns,
                                           run_command, self.log)
        if return_code != 0:
            self.log.warn("Failed on run step")
            return return_code

        self.log.info(f"---- Ended task with json file: {tail}  " +
                      f"Return_code: {return_code}")
        return return_code

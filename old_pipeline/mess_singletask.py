#
# Runs a single job on a single machine for MESS
#
import os.path

from old_pipeline import util
from old_pipeline.singletask import SingleTask

# Where to find tasks.  Be sure to have '/' at end
all_tasks_dir = "/home/ubuntu/tasks/passive/all/"
current_tasks_dir = "/home/ubuntu/mess_original_code/mess_final/tasks/"

# The command that will be run to process a scene
run_command = "cd /home/ubuntu/mess_original_code/mess_final/ && ./mess_runall.sh"


class MessSingleTask(SingleTask):

    def process(self):
        head, tail = os.path.split(self.json_file_name)
        self.log.info(f"---- Starting task with json file: {tail}")

        # Clear out current tasks
        cmd = "rm -f " + current_tasks_dir + "* || true"
        return_code = util.shell_run_command_remote(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on rm old tasks step")
            return return_code

        # Copy the file from task dir to current task dir
        cmd = "cp " + all_tasks_dir + tail + " " + current_tasks_dir
        return_code = util.shell_run_command_remote(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on cp new tasks step")
            return return_code

        # Run the command
        return_code = util.shell_run_command_remote(self.machine_dns,
                                                    run_command, self.log)
        if return_code != 0:
            self.log.warn("Failed on run step")
            return return_code

        self.log.info(f"---- Ended task with json file: {tail}  " +
                      f"Return_code: {return_code}")
        return return_code

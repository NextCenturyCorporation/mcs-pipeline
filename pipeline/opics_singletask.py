#
# Runs a single job on a single machine for OPICS
#
import os.path

from pipeline import util
from pipeline.singletask import SingleTask

# Where to find tasks.  Be sure to have '/' at end
local_scene_dir = "/home/clark/work/mcs/eval3.5/data/eval/"
current_tasks_dir = "/home/ubuntu/mcs_eval3-3.5.0/gravity_scenes/"

# The command that will be run to process a scene
run_command = "cd /home/ubuntu/mcs_eval3-3.5.0 " \
              "&& source activate mcs_opics " \
              "&& python3 eval.py --scenes gravity_scenes"


class OpicsSingleTask(SingleTask):

    def process(self):
        head, scene_file = os.path.split(self.json_file_name)
        self.log.info(f"---- Starting task with json file: {scene_file}")

        # Clear out current tasks
        cmd = "rm -f " + current_tasks_dir + "* || true"
        return_code = util.shell_run_command_remote(self.machine_dns, cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on rm old tasks step")
            return return_code

        # Copy the scene file to the correct place on the remote machine
        local_file = local_scene_dir + scene_file
        util.copy_file_to_aws(self.machine_dns,
                              local_file, self.log, current_tasks_dir)

        # Run the command
        return_code = util.shell_run_command_remote(self.machine_dns,
                                                    run_command, self.log)
        if return_code != 0:
            self.log.warn("Failed on run step")
            return return_code

        self.log.info(f"---- Ended task with json file: {scene_file}  " +
                      f"Return_code: {return_code}")
        return return_code

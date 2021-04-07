#
# Runs a single job on a single machine for MESS
#
import os.path

from pipeline import util
from pipeline.singletask import SingleTask

# Where to find tasks.  Be sure to have '/' at end
local_scene_dir = "/home/clark/work/mcs/eval3.5/data/eval/"
remote_scene_dir = "/home/ubuntu/workspace/scenes/"


class CoraSingleTask(SingleTask):

    def process(self):
        head, scene_file = os.path.split(self.json_file_name)
        self.log.info(f"---- Starting task with json file: {scene_file}")

        # Copy the scene file to the correct place on the remote machine
        local_file = local_scene_dir + scene_file
        util.copy_file_to_aws(self.machine_dns,
                              local_file, self.log, remote_scene_dir)

        # Change the name of the file in ./run_cora.sh
        old_scene = "gravity_support_ex_05.json"
        mod_command = 'sed "s/' + old_scene + '/' + scene_file + '/" ' + \
                      '/home/ubuntu/run_cora.sh > /home/ubuntu/r.sh ' + \
                      '&& chmod +x /home/ubuntu/r.sh'
        return_code = util.shell_run_command(self.machine_dns,
                                             mod_command, self.log)
        if return_code != 0:
            self.log.warn("Failed on sed step")
            return return_code

        # Run the command
        return_code = util.shell_run_command(self.machine_dns,
                                             "/home/ubuntu/r.sh", self.log)
        if return_code != 0:
            self.log.warn("Failed on run step")
            return return_code

        self.log.info(f"---- Ended task with json file: {scene_file}  " +
                      f"Return_code: {return_code}")
        return return_code

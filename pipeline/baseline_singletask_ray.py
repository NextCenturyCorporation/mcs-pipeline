#
# Runs a single baseline job.
#
# Note:  This code is run by ray on the machine, so can do things locally;  no ssh
#
import glob
import os
import traceback
from shutil import copyfile

from pipeline import util
from pipeline.logger import configure_logging

# The baseline code runs all the scenes in this directory.
# dir_with_scenes_for_running = '/home/ubuntu/scenes/validation/'
dir_with_scenes_for_running = "/home/clark/work/mcs/eval3.5/data/baseline_broken/"

# The directory with all the scenes in it
# dir_with_all_scenes = '/home/ubuntu/tasks/'
dir_with_all_scenes = '/home/clark/work/mcs/eval3.5/data/eval/'

run_cmd = "bash -c 'cd /home/clark/work/mcs/eval3.5/baseline && source venv/bin/activate && python3 gravity_py.py'"
# run_cmd = "bash -c 'cd /home/ubuntu/ && source venv/bin/activate && python3 gravity_py.py'"

class BaselineSingleTaskRay:

    def __init__(self, json_file_name, log):
        self.json_file_name = json_file_name

        if log is None:
            self.log = configure_logging("BaselineSingleTaskRay", "logfile.txt")

    def process(self):

        # Make sure that X is running, start it if it is not
        xorg_running = util.check_if_process_running("Xorg")

        if xorg_running:
            self.log.info("xorg is running")
        else:
            self.log("xorg not running;  trying to start")
            cmd = "cd ~/mcs-pipeline/ && sudo python3 run_startx.py &"
            util.run_command_and_return(cmd, self.log)

        try:
            # Remove files from running dir
            files = glob.glob(dir_with_scenes_for_running+"*")
            for f in files:
                os.remove(f)

            # Copy scene file from all scenes dir to running directory
            scene_file_in_all = dir_with_all_scenes + self.json_file_name
            scene_file_in_run = dir_with_scenes_for_running + self.json_file_name
            copyfile(scene_file_in_all, scene_file_in_run)
        except Exception as e:
            traceback.print_exc()
            self.log.warn("Unable to clear our dir and copy scene" + str(e))
            return -1

        return_code = util.run_command_and_capture_output(run_cmd, self.log)
        if return_code != 0:
            self.log.warn("Failed on run step")
            return return_code

        return return_code



if __name__ == '__main__':
    try:
        b = BaselineSingleTaskRay("juliett_0001_19.json", None)
        b.process()
    except:
        traceback.print_exc()
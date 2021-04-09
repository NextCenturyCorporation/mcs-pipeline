#
# Runs a single baseline job.
#
# Note:  This code is run by ray on the machine, so can do things locally;  no ssh
#
import glob
import os
from shutil import copyfile

from pipeline import util
from pipeline.logger import configure_logging

# The baseline code runs all the scenes in this directory.
dir_with_scenes_for_running = '/home/ubuntu/scenes/validation/'

# The directory with all the scenes in it
dir_with_all_scenes = '/home/ubuntu/tasks/'


class BaselineSingleTaskRay:

    def __init__(self, json_file_name, log):
        self.json_file_name = json_file_name

        if log is None:
            self.log = configure_logging("BaselineSingltTaskRay", "/tmp/logfile.txt")

    def process(self):

        # Make sure that X is running, start it if it is not
        xorg_running = util.check_if_process_running("Xorg")
        if not xorg_running:
            cmd = "cd ~/mcs-pipeline/ && sudo python3 run_startx.py &"
            # util.

        try:
            # Remove files from running dir
            files = glob.glob(dir_with_scenes_for_running)
            for f in files:
                os.remove(f)

            # Copy scene file from all scenes dir to running directory
            scene_file_in_all = dir_with_all_scenes + self.json_file_name
            scene_file_in_run = dir_with_scenes_for_running + self.json_file_name
            copyfile(scene_file_in_all, scene_file_in_run)
        except Exception as e:
            self.log.warn("Unable to clear our dir and copy scene" + str(e))
            return -1

        return_code = 1

        return return_code

#
# Use Ray to run all the scenes.
#
# Usage:   python pipeline_ray.py configs/execution_config.ini configs/mcs_config.ini
#          where execution_config.ini has run_script and scenes information
#                mcs_config.ini has metadata level, team, evaluation, etc.
#
import argparse
import configparser
import json
import os
import pathlib
import time
import traceback
import uuid

import ray

from pipeline import logger
from pipeline import util


@ray.remote
class MCSRayActor:
    """Ray Actor that calls a script on the remote machine """

    def __init__(self, run_script: str):
        self.identifier = uuid.uuid4()
        self.run_script = run_script

    def run_scene(self, mcs_config, scene_config):
        # Save the mcs_config information as /tmp/mcs_config.ini
        mcs_config_filename = "/tmp/mcs_config.ini"
        print(f"Saving mcs config information to {mcs_config_filename}")
        with open(mcs_config_filename, 'w') as mcs_config_file:
            for line in mcs_config:
                mcs_config_file.write(line)

        # Save the scene config information
        scene_config_filename = "/tmp/" + str(self.identifier) + ".json"
        print(f"Saving scene information to {scene_config_filename}")
        with open(scene_config_filename, 'w') as scene_config_file:
            json.dump(scene_config, scene_config_file)

        # Run the script on the machine
        cmd = f'{self.run_script} {mcs_config_filename} {scene_config_filename}'
        print(f"In run scene.  Running {cmd}")

        # TODO:  Return more information from the script about how it went and results
        ret = os.system(cmd)

        # TODO:  Remove the mcs_config.ini file since it may have AWS information in it

        # TODO:  Long term.  copy the files to S3???

        return ret


class SceneRunner:

    def __init__(self, args):

        # Get Execution Configuration, which has scene information and how to run scripts on the worker machines
        self.exec_config = configparser.ConfigParser()
        self.exec_config.read(args.execution_config_file)

        # Get MCS configuration, which has infomation about how to run the MCS code, metadata level, etc.
        self.mcs_config = self.read_mcs_config(args.mcs_config_file)

        self.scene_files_list = []

        date_str = util.get_date_in_file_format()
        self.log = logger.configure_base_logging(date_str + ".log")
        self.log.info("Starting run scenes")

        self.get_scenes()
        self.run_scenes()

    def read_mcs_config(selfs, mcs_config_filename: str):
        with open(mcs_config_filename, 'r') as mcs_config_file:
            lines = mcs_config_file.readlines()
        return lines

    def get_scenes(self):
        """Read the scene files to use from the argument scene_list"""

        base_dir = pathlib.Path(self.exec_config['MCS']['scene_location'])
        task_file = open(self.exec_config['MCS']['scene_list'], 'r')
        lines = task_file.readlines()
        for line in lines:
            if line is not None and len(line) > 0:
                self.scene_files_list.append(base_dir / line.strip())

        self.scene_files_list.sort()
        self.log.info(f"Number of scenes: {len(self.scene_files_list)}")
        self.log.info(f"Scenes {self.scene_files_list}")

    def run_scenes(self):

        mcs_actor = MCSRayActor.remote(
            run_script=self.exec_config['MCS']['run_script']
        )
        self.log.info(f"Running {len(self.scene_files_list)} scenes")
        job_ids = []
        for scene_ref in self.scene_files_list:
            with open(str(scene_ref)) as scene_file:
                job_ids.append(mcs_actor.run_scene.remote(self.mcs_config, json.load(scene_file)))

        not_done = job_ids
        while not_done:
            done, not_done = ray.wait(not_done)
            for done_ref in done:
                result = ray.get(done_ref)
                self.log.info(f"Result of {done_ref}:  {result}")


def parse_args():
    parser = argparse.ArgumentParser(description='Run scenes using ray')
    parser.add_argument(
        'execution_config_file',
        help='Ini file that describes scenes and what script to run for a performer')
    parser.add_argument(
        'mcs_config_file',
        help='Ini file that describes MCS configuration, debug, metadata, team, etc. '
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    # TODO:  If running local, do ray.init().  If doing remote/cluster, do (address='auto').  Add
    # command line switch to determine which to use
    # ray.init(address='auto')
    ray.init()

    try:
        scene_runner = SceneRunner(args)
    except Exception as e:
        print(f"exception {e}")
        traceback.print_exc()

    # Give it time to wrap up, produce output from the ray workers
    time.sleep(2)
    print("\n*********************************")
    input("Finished.  Hit enter to finish ")

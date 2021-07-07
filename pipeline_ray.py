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
import pathlib
import time
import traceback
import uuid
import subprocess
import io
from dataclasses import dataclass, field
from typing import List

import ray


@ray.remote(num_gpus=1)
def run_scene(run_script, mcs_config, scene_config):
    """ Ray """

    identifier = uuid.uuid4()
    run_script = run_script

    # Save the mcs_config information as /tmp/mcs_config.ini
    mcs_config_filename = "/tmp/mcs_config.ini"
    print(f"Saving mcs config information to {mcs_config_filename}")
    with open(mcs_config_filename, 'w') as mcs_config_file:
        for line in mcs_config:
            mcs_config_file.write(line)

    # Save the scene config information
    scene_config_filename = "/tmp/" + str(identifier) + ".json"
    print(f"Saving scene information to {scene_config_filename}")
    with open(scene_config_filename, 'w') as scene_config_file:
        json.dump(scene_config, scene_config_file)

    # Run the script on the machine
    cmd = f'{run_script} {mcs_config_filename} {scene_config_filename}'
    print(f"In run scene.  Running {cmd}")

    proc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines=[]
    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        print(line.rstrip())
        lines.append(line)
    ret=proc.wait()
    output = ''.join(lines)

    # TODO MCS-702:  Send AWS S3 Parameters in Pipeline, Make them Ephemeral.  Until MCS-674, which will
    # move it entirely to the pipeline

    # TODO  MCS-674:  Move Evaluation Code out of Python API (and into the pipeline)

    return ret, output

@dataclass
class RunStatus:
    exit_code: int
    output: str
    status: str 
    job_id = None
    retry: bool = False

@dataclass
class SceneStatus:
    scene_file: str
    retries: int = 0
    status: str = ""
    run_statuses: List[RunStatus] = field(default_factory=list)
    
class SceneRunner:

    scene_statuses={}
    # Valid properties for various fields in mcs_config_file
    METADATA_LVLS = ["level1", "level2", "oracle"]
    EVAL_NAMES = ["eval_3-75", "eval_4", "eval_5", "eval_6", "eval_7", "eval_8"]
    TEAM_NAMES = ["mess", "mit", "opics", "baseline"]
    # TODO: MCS-754: Need to make the following properties more flexible for Eval 4+ and update folder structure
    CURRENT_EVAL_BUCKET = "evaluation-images"
    CURRENT_EVAL_FOLDER = "eval-3.75"

    def __init__(self, args):

        # Get Execution Configuration, which has scene information and how to run scripts on the worker machines
        self.exec_config = configparser.ConfigParser()
        self.exec_config.read(args.execution_config_file)
        self.disable_validation = args.disable_validation

        # Get MCS configuration, which has infomation about how to run the MCS code, metadata level, etc.
        self.check_for_valid_mcs_config(args.mcs_config_file)
        self.mcs_config = self.read_mcs_config(args.mcs_config_file)

        self.scene_files_list = []

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        print(f"Starting run scenes {date_str}")

        self.get_scenes()
        self.run_scenes()
        self.print_results()

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        print(f"Finished run scenes {date_str}")

    def print_results(self):
        # scenes may have multiple entries of they were retried
        scenes_printed = []
        print("Status:")
        for key in self.scene_statuses:
            s_status=self.scene_statuses[key]
            file=s_status.scene_file
            if file not in scenes_printed:
                scenes_printed.append(file)
                self.print_scene_status(s_status,"  ")
    
    def print_scene_status(self, s_status, prefix=""):
        print(f"{prefix}Scene: {s_status.status} - {s_status.scene_file}")
        print(f"{prefix}  retries: {s_status.retries}")
        for x,run in enumerate(s_status.run_statuses):
            print(f"{prefix}  Attempt {x}")
            self.print_run_status(run, "      ")

    def print_run_status(self, run, prefix=""):
        print(f"{prefix}Code: {run.exit_code}")
        print(f"{prefix}Status: {run.status}")
        print(f"{prefix}Retryable: {run.retry}")

    def read_mcs_config(self, mcs_config_filename: str):
        with open(mcs_config_filename, 'r') as mcs_config_file:
            lines = mcs_config_file.readlines()
        return lines

    def check_for_valid_mcs_config(self, config_file_path):
        if(self.disable_validation == False):
            mcs_config_parse = configparser.ConfigParser()
            mcs_config_parse.read(config_file_path)

            valid = True

            if(mcs_config_parse['MCS']['evaluation'] != 'true'):
                print('Error: Evaluation property in MCS config file is not set to true.')
                valid = False
            if(mcs_config_parse['MCS']['s3_bucket'] != self.CURRENT_EVAL_BUCKET):
                print('Error: MCS Config file does not have the correct s3 bucket specified.')
                valid = False
            if(mcs_config_parse['MCS']['s3_folder'] != self.CURRENT_EVAL_FOLDER):
                print('Error: MCS Config file does not have the correct s3 folder specified.')
                valid = False
            if(mcs_config_parse['MCS']['metadata'] not in self.METADATA_LVLS):
                print('Error: MCS Config file does not include valid metadata level.')
                valid = False
            if(mcs_config_parse['MCS']['evaluation_name'] not in self.EVAL_NAMES):
                print('Error: MCS Config file does not include valid evaluation_name.')
                valid = False
            if(mcs_config_parse['MCS']['team'] not in self.TEAM_NAMES):
                print('Error: MCS Config file does not include valid team name.')
                valid = False

            if(valid == False):
                raise Exception('Invalid property value in MCS config file.')

    def get_scenes(self):
        """Read the scene files to use from the argument scene_list"""

        base_dir = pathlib.Path(self.exec_config['MCS']['scene_location'])
        task_file = open(self.exec_config['MCS']['scene_list'], 'r')
        lines = task_file.readlines()
        for line in lines:
            if line is not None and len(line) > 0:
                self.scene_files_list.append(base_dir / line.strip())

        self.scene_files_list.sort()
        print(f"Number of scenes: {len(self.scene_files_list)}")
        print(f"Scenes {self.scene_files_list}")

    def run_scenes(self):
        # This should probably be configurable and may need to be different depending on what errors we are detecting.
        # This should work for a first step though.
        num_retries = 3
        print(f"Running {len(self.scene_files_list)} scenes")
        job_ids = []
        for scene_ref in self.scene_files_list:
            with open(str(scene_ref)) as scene_file:
                job_id = run_scene.remote(self.exec_config['MCS']['run_script'], self.mcs_config, json.load(scene_file))
                self.scene_statuses[job_id] = SceneStatus(scene_ref, 0, "pending")
                job_ids.append(job_id)

        not_done = job_ids
        while not_done:
            done, not_done = ray.wait(not_done)
            for done_ref in done:
                result,output = ray.get(done_ref)
                scene_status = self.scene_statuses.get(done_ref)
                run_status = self.get_run_status(result, output, scene_status.scene_file)
                scene_status.run_statuses.append(run_status)
                print(f"file: {scene_status.scene_file}")
                self.print_run_status(run_status)
                if (run_status.retry and scene_status.retries < num_retries):
                    self.do_retry(not_done, scene_status)
                    scene_status.retries += 1
                    scene_status.status = "retrying"
                else:
                    # If we are finished, full scene status should be same as last run status
                    scene_status.status = run_status.status
                print(f"{len(not_done)}  Result of {done_ref}:  {result}")

    def do_retry(self, not_done, scene_status):
        scene_ref=scene_status.scene_file
        with open(str(scene_ref)) as scene_file:
            job_id = run_scene.remote(self.exec_config['MCS']['run_script'],self.mcs_config, json.load(scene_file))
            print(f"Retrying {scene_ref} with job_id={job_id}")
            self.scene_statuses[job_id] = scene_status
            not_done.append(job_id)

    def get_run_status(self, result:int, output:str, scene_file_path:str) -> RunStatus:
        status = RunStatus(result, output, "Success", False)
        # Result is really the result of the copy result files (or last command in ray_script.sh)
        if result is not 0:
            status.retry |= False
            status.status = "Error"
        if "Exception in create_controller() Time out!" in output:
            print(f"Timeout occured for file={scene_file_path}")
            status.retry |= True
            status.status = "Error: Timeout"
        # Add more conditions to retry here
        return status

def parse_args():
    parser = argparse.ArgumentParser(description='Run scenes using ray')
    parser.add_argument(
        'execution_config_file',
        help='Ini file that describes scenes and what script to run for a performer')
    parser.add_argument(
        'mcs_config_file',
        help='Ini file that describes MCS configuration, debug, metadata, team, etc. '
    )
    parser.add_argument(
        '--disable_validation',
        default=False,
        action='store_true',
        help='Whether or not to skip validatation of MCS config file'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    # TODO MCS-711:  If running local, do ray.init().  If doing remote/cluster, do (address='auto').
    #  Add command line switch or configuration to determine which to use
    ray.init(address='auto')
    # ray.init()

    try:
        scene_runner = SceneRunner(args)
    except Exception as e:
        print(f"exception {e}")
        traceback.print_exc()

    # Give it time to wrap up, produce output from the ray workers
    time.sleep(2)
    print("\n*********************************")
    input("Finished.  Hit enter to finish ")

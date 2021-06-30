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

    cmd = f'{run_script} {mcs_config_filename} {scene_config_filename}'#' | tee {out_file_path}'
    print(f"In run scene.  Running {cmd}") 

    proc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines=[]
    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        print(line.rstrip())
        lines.append(line)
    output = ''.join(lines)

    # TODO MCS-702:  Send AWS S3 Parameters in Pipeline, Make them Ephemeral.  Until MCS-674, which will
    # move it entirely to the pipeline

    # TODO  MCS-674:  Move Evaluation Code out of Python API (and into the pipeline)

    print("about to return")
    return proc.returncode, output


class SceneRunner:

    retry_counts={}

    def __init__(self, args):

        # Get Execution Configuration, which has scene information and how to run scripts on the worker machines
        self.exec_config = configparser.ConfigParser()
        self.exec_config.read(args.execution_config_file)

        # Get MCS configuration, which has infomation about how to run the MCS code, metadata level, etc.
        self.mcs_config = self.read_mcs_config(args.mcs_config_file)

        self.scene_files_list = []

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        print(f"Starting run scenes {date_str}")

        self.get_scenes()
        self.run_scenes()

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        print(f"Finished run scenes {date_str}")

    def read_mcs_config(self, mcs_config_filename: str):
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
        print(f"Number of scenes: {len(self.scene_files_list)}")
        print(f"Scenes {self.scene_files_list}")

    def run_scenes(self):
        id_to_scene_file={}

        print(f"Running {len(self.scene_files_list)} scenes")
        job_ids = []
        for scene_ref in self.scene_files_list:
            with open(str(scene_ref)) as scene_file:
                job_id=run_scene.remote(self.exec_config['MCS']['run_script'],self.mcs_config, json.load(scene_file))
                id_to_scene_file[job_id]=scene_ref
                job_ids.append(job_id)

        not_done = job_ids
        while not_done:
            done, not_done = ray.wait(not_done)
            for done_ref in done:
                result,output = ray.get(done_ref)
                if (self.is_retry(result, output,scene_ref)):
                    scene_ref=id_to_scene_file[done_ref]
                    with open(str(scene_ref)) as scene_file:
                        job_id=run_scene.remote(self.exec_config['MCS']['run_script'],self.mcs_config, json.load(scene_file))
                        print(f"Retrying {scene_ref} with job_id={job_id}")
                        id_to_scene_file[job_id]=scene_ref
                        not_done.append(job_id)
                print(f"{len(not_done)}  Result of {done_ref}:  {result}")

    def is_retry(self, result:int, output:str, scene_file_path:str) -> bool:
        num_retries = self.retry_counts.get(scene_file_path, 0)
        retry=False
        if ("Exception in create_controller() Time out!" in output and num_retries < 1):
            print(f"Timeout occured for file={scene_file_path}")
            retry|=True
        #Allow for more conditions to retry
        if (retry):
            self.retry_counts[scene_file_path]=num_retries+1
            return True

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

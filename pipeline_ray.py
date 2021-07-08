#
# Use Ray to run all the scenes.
#
# Usage:   python pipeline_ray.py configs/execution_config.ini configs/mcs_config.ini
#          where execution_config.ini has run_script and scenes information
#                mcs_config.ini has metadata level, team, evaluation, etc.
#
import argparse
import configparser
import datetime
import json
import pathlib
import time
import uuid
import subprocess
import io
import logging
from dataclasses import dataclass, field
from typing import List
from logging import config

import ray
import boto3

# This is logging for head node during setup and distribution.  
logging.basicConfig(level=logging.DEBUG,format="%(message)s")

def push_to_s3(source_file: pathlib, bucket: str, s3_filename: str, mimetype:str='text/plain', client=None):
    if client is None:
        client = boto3.client('s3')
    logging.debug(f"Pushing {str(source_file)} to {bucket} / {s3_filename}")
    client.upload_file(
            str(source_file),
            bucket,
            s3_filename,
            ExtraArgs={
                'ACL': 'public-read',
                'ContentType': mimetype,
            }
    )

@ray.remote(num_gpus=1)
def run_scene(run_script, mcs_config, scene_config, scene_try):
    """ Ray """
    scene_name = scene_config.get("name","")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    config = configparser.ConfigParser()
    config.read_string("\n".join(mcs_config))

    log_dir = pathlib.Path("/tmp/results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    # Do we want the timestamp?  If so, we will leave a bunch of log files on a single machien.  
    # Do we clean up files?  If we don't do the timestamp, we will need to cleanup logs here so we 
    # don't end up with old executes logs at the top of a new execution.  This may not really happen 
    # in real evals, but happens when testing often.
    log_file = log_dir.joinpath(f"{scene_name}-{scene_try}-{timestamp}.log")
    setup_logging(log_file)

    identifier = uuid.uuid4()
    run_script = run_script

    # Save the mcs_config information as /tmp/mcs_config.ini
    mcs_config_filename = "/tmp/mcs_config.ini"
    logging.info(f"Saving mcs config information to {mcs_config_filename}")
    with open(mcs_config_filename, 'w') as mcs_config_file:
        for line in mcs_config:
            mcs_config_file.write(line)

    # Save the scene config information
    scene_config_filename = "/tmp/" + str(identifier) + ".json"
    logging.info(f"Saving scene information to {scene_config_filename}")
    with open(scene_config_filename, 'w') as scene_config_file:
        json.dump(scene_config, scene_config_file)

    # Run the script on the machine
    cmd = f'{run_script} {mcs_config_filename} {scene_config_filename}'
    logging.info(f"In run scene.  Running {cmd}")

    proc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = []
    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        logging.info(line.rstrip())
        lines.append(line)
    ret = proc.wait()
    output = ''.join(lines)

    # TODO MCS-702:  Send AWS S3 Parameters in Pipeline, Make them Ephemeral.  Until MCS-674, which will
    # move it entirely to the pipeline

    # TODO  MCS-674:  Move Evaluation Code out of Python API (and into the pipeline)

    logs_to_s3 = config.getboolean("MCS", "logs_to_s3", fallback=True)
    if (logs_to_s3):
        # This seems a little dirty, but its mostly copied from MCS project.
        bucket = config.get("MCS", "s3_bucket")
        folder = config.get("MCS", "s3_folder")
        eval_name = config.get("MCS", "evaluation_name")
        team = config.get("MCS", "team")
        metadata = config.get("MCS", "metadata")
        s3_filename = folder + "/" + '_'.join(
                [eval_name, metadata,
                team,
                scene_name, timestamp,
                "log"]) + '.txt'

        # Might need to find way to flush logs and/or stop logging.
        push_to_s3(log_file, bucket, s3_filename)

    logging.shutdown()
    log_file.unlink()

    return ret, output

def setup_logging(log_file):
    # Need to initialize because its on a remote machine.
    log_config = {
        "version": 1,
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "log-file"],
            "propagate": False
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "level": "DEBUG",
                "stream": "ext://sys.stdout"
            },
            "log-file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "brief",
                "filename": "",
                "maxBytes": 10240000,
                "backupCount": 1
            }
        },
        "formatters": {
            "brief": {
                "format": "%(message)s"
            },
            "precise": {
                "format": "%(asctime)s <%(levelname)s>: %(message)s"
            },
            "full": {
                "format": "[%(name)s] %(asctime)s <%(levelname)s>: " +
                "%(message)s"
            }
        }
    }
    log_config["handlers"]["log-file"]["filename"]=str(log_file)
    config.dictConfig(log_config)

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

    def __init__(self, args):

        # Get Execution Configuration, which has scene information and how to run scripts on the worker machines
        self.exec_config = configparser.ConfigParser()
        self.exec_config.read(args.execution_config_file)

        # Get MCS configuration, which has infomation about how to run the MCS code, metadata level, etc.
        self.mcs_config = self.read_mcs_config(args.mcs_config_file)

        self.scene_files_list = []

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        logging.info(f"Starting run scenes {date_str}")

        self.get_scenes()
        self.run_scenes()
        self.print_results()

        date_str = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        logging.info(f"Finished run scenes {date_str}")

    def print_results(self):
        # scenes may have multiple entries of they were retried
        scenes_printed = []
        logging.info("Status:")
        for key in self.scene_statuses:
            s_status = self.scene_statuses[key]
            file = s_status.scene_file
            if file not in scenes_printed:
                scenes_printed.append(file)
                self.print_scene_status(s_status,"  ")
    
    def print_scene_status(self, s_status, prefix=""):
        logging.info(f"{prefix}Scene: {s_status.status} - {s_status.scene_file}")
        logging.info(f"{prefix}  retries: {s_status.retries}")
        for x,run in enumerate(s_status.run_statuses):
            logging.info(f"{prefix}  Attempt {x}")
            self.print_run_status(run, "      ")

    def print_run_status(self, run, prefix=""):
        logging.info(f"{prefix}Code: {run.exit_code}")
        logging.info(f"{prefix}Status: {run.status}")
        logging.info(f"{prefix}Retryable: {run.retry}")

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
        logging.info(f"Number of scenes: {len(self.scene_files_list)}")
        logging.info(f"Scenes {self.scene_files_list}")

    def run_scenes(self):
        num_retries = 3
        logging.info(f"Running {len(self.scene_files_list)} scenes")
        job_ids = []
        for scene_ref in self.scene_files_list:
            with open(str(scene_ref)) as scene_file:
                job_id = run_scene.remote(self.exec_config['MCS']['run_script'], self.mcs_config, json.load(scene_file), 1)
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
                logging.info(f"file: {scene_status.scene_file}")

                self.print_run_status(run_status)
                if (run_status.retry and scene_status.retries < num_retries):
                    self.do_retry(not_done, scene_status)
                    scene_status.retries += 1
                    scene_status.status = "retrying"
                else:
                    # If we are finished, full scene status should be same as last run status
                    scene_status.status = run_status.status
                logging.info(f"{len(not_done)}  Result of {done_ref}:  {result}")

    def do_retry(self, not_done, scene_status:SceneStatus):
        scene_ref = scene_status.scene_file
        with open(str(scene_ref)) as scene_file:
            #Retries is +2 to get test number because +1 for next run increment and +1 for changing to 0 base to 1 base index
            job_id = run_scene.remote(self.exec_config['MCS']['run_script'],self.mcs_config, json.load(scene_file), scene_status.retries + 2)
            logging.info(f"Retrying {scene_ref} with job_id={job_id}")
            self.scene_statuses[job_id] = scene_status
            not_done.append(job_id)

    def get_run_status(self, result:int, output:str, scene_file_path:str) -> RunStatus:
        status = RunStatus(result, output, "Success", False)
        # Result is really the result of the copy result files (or last command in ray_script.sh)
        if result is not 0:
            status.retry |= False
            status.status = "Error"
        if "Exception in create_controller() Time out!" in output:
            logging.info(f"Timeout occured for file={scene_file_path}")
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
        logging.info(f"Exception: ", exc_info=e)

    # Give it time to wrap up, produce output from the ray workers
    time.sleep(2)
    logging.info("\n*********************************")
    input("Finished.  Hit enter to finish ")

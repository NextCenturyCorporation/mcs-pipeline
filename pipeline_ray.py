#
# Use Ray to run all the scenes.
#
# Usage:
#    python pipeline_ray.py configs/execution_config.ini configs/mcs_config.ini
#           where execution_config.ini has run_script and scenes information
#                 mcs_config.ini has metadata level, team, evaluation, etc.
#
# This code run individual scenes (as specified in the execution_config) on
# Ray worker machines. Each scene is run by the run_scene function as a Ray
# remote task, which just calls the script specified in execution_config.
import argparse
import configparser
import datetime
import glob
import io
import json
import logging
import os
import pathlib
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from logging import config
from typing import List

import boto3
import ray

# Number of retries before we give up on a job and call it failed
NUM_RETRIES = 3

# File the records the files that finished.  If we want to restart,
# we can skip these files.
FINISHED_SCENES_LIST_FILENAME = "./.last_run_finished.txt"

# This is logging for head node during setup and distribution.
logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def push_to_s3(
    source_file: pathlib,
    bucket: str,
    s3_filename: str,
    mimetype: str = "text/plain",
    client=None,
):
    """Copy a file to a S3 bucket"""
    if client is None:
        client = boto3.client("s3")
    logging.debug(f"Pushing {source_file} to {bucket}/{s3_filename}")
    client.upload_file(
        str(source_file),
        bucket,
        s3_filename,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": mimetype,
        },
    )


@ray.remote(num_gpus=1)
def run_scene(
    run_script,
    mcs_config: configparser.ConfigParser,
    scene_config,
    eval_dir,
    scene_try,
):
    """Code to run a single scene on a worker machine using Ray.
    This function should not have code dependencies because they
    are not automatically copied to remote machines.

    :param run_script: Script on worker machine (must exist) to run scene
    :param mcs_config: Standard MCS config info
    :param scene_config: Scene json file, in json object
    :param scene_try: Integer, try number (1, 2, etc.)
    :return: result: script return code, output: script stdout/err output
    :rtype (int, str)"""

    scene_name = scene_config.get("name", "")

    # replace slashes in filenames with dashes
    scene_name = scene_name.replace("/", "-")

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    log_dir = pathlib.Path("/tmp/results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    # Do we want the timestamp?  If so, we will leave a bunch of log files
    # on a single machine.
    # Do we clean up files?  If we don't do the timestamp, we will need to
    # cleanup logs here so we don't end up with old executes logs at the
    # top of a new execution.  This may not really happen in real evals, but
    # happens when testing often.
    log_file = log_dir.joinpath(f"{scene_name}-{scene_try}-{timestamp}.log")
    setup_logging(log_file)

    identifier = uuid.uuid4()
    run_script = run_script

    # Save the mcs_config information as /tmp/mcs_config.ini
    mcs_config_filename = "/tmp/mcs_config.ini"
    logging.info(f"Saving mcs config information to {mcs_config_filename}")

    with open(mcs_config_filename, "w") as mcs_config_file:
        mcs_config.write(mcs_config_file)

    # Save the scene config information
    scene_config_filename = "/tmp/" + str(identifier) + ".json"
    logging.info(f"Saving scene information to {scene_config_filename}")
    with open(scene_config_filename, "w") as scene_config_file:
        json.dump(scene_config, scene_config_file)

    # Run the script on the machine
    cmd = (
        f"{run_script} {mcs_config_filename}"
        f" {scene_config_filename} {eval_dir}"
    )
    logging.info(f"In run scene.  Running {cmd}")

    proc = subprocess.Popen(
        cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    lines = []
    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        logging.info(line.rstrip())
        lines.append(line)
    result = proc.wait()
    output = "".join(lines)

    evaluation = mcs_config.getboolean("MCS", "evaluation", fallback=False)
    movies_folder = mcs_config.get("MCS", "s3_movies_folder", fallback=None)
    bucket = mcs_config.get("MCS", "s3_bucket", fallback=None)
    folder = mcs_config.get("MCS", "s3_folder", fallback=None)
    eval_name = mcs_config.get("MCS", "evaluation_name")
    team = mcs_config.get("MCS", "team")
    metadata = mcs_config.get("MCS", "metadata")
    # video_enabled =
    # mcs_config.getboolean("MCS", "video_enabled", fallback=False)

    if evaluation:
        # find scene history file (should only be one file in directory)
        scene_hist_matches = glob.glob(
            eval_dir + "/SCENE_HISTORY/" + scene_name + "*.json"
        )

        if len(scene_hist_matches) > 0:
            found_scene_hist = max(scene_hist_matches, key=os.path.getctime)
            hist_filename_no_ext = os.path.splitext(found_scene_hist)[0]
            timestamp = hist_filename_no_ext[-15:]

            logging.info("History file timestamp: " + timestamp)

            scene_hist_dest = (
                folder
                + "/"
                + "_".join([eval_name, metadata, team, scene_name])
                + ".json"
            )

            scene_hist_file = pathlib.Path(found_scene_hist)

            # upload scene history
            push_to_s3(
                scene_hist_file, bucket, scene_hist_dest, "application/json"
            )
        else:
            logging.warning("History file not found for scene " + scene_name)

        # find and upload videos
        find_video_files = glob.glob(
            eval_dir + "/" + scene_name + "/*" + timestamp + ".mp4"
        )

        if len(find_video_files) == 0:
            logging.warning(
                "No video files found for scene "
                + scene_name
                + " and timestamp "
                + timestamp
            )

        for vid_file in find_video_files:
            # type of video (depth, segmentation, etc) should be at the
            # end of the filename, before timestamp
            vid_type = vid_file.split("_")[-2]

            video_folder = (
                movies_folder if movies_folder is not None else folder
            )

            vid_file_dest = (
                video_folder
                + "/"
                + "_".join([eval_name, metadata, team, scene_name, vid_type])
                + ".mp4"
            )

            vid_file_path = pathlib.Path(vid_file)

            push_to_s3(vid_file_path, bucket, vid_file_dest, "video/mp4")

    logs_to_s3 = mcs_config.getboolean("MCS", "logs_to_s3", fallback=True)
    if logs_to_s3:
        # This seems a little dirty, but its mostly copied from MCS project.

        # Upload timestamped version, and write/overwrite a 
        # seperate "latest" log file
        log_s3_filename_timestamp = (
            folder
            + "/"
            + "_".join(
                [eval_name, metadata, team, scene_name, timestamp, "log"]
            )
            + ".txt"
        )

        log_s3_filename_latest = (
            folder
            + "/"
            + "_".join(
                [eval_name, metadata, team, scene_name, "latest", "log"]
            )
            + ".txt"
        )

        # Might need to find way to flush logs and/or stop logging.
        push_to_s3(log_file, bucket, log_s3_filename_timestamp)
        push_to_s3(log_file, bucket, log_s3_filename_latest)

    logging.shutdown()
    log_file.unlink()

    return result, output


def setup_logging(log_file):
    # Need to initialize because its on a remote machine.
    log_config = {
        "version": 1,
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "log-file"],
            "propagate": False,
        },
        "loggers": {
            "s3transfer": {
                "level": "INFO",
                "handlers": ["console", "log-file"],
                "propagate": False,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            },
            "log-file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "brief",
                "filename": "",
                "maxBytes": 10240000,
                "backupCount": 1,
            },
        },
        "formatters": {
            "brief": {"format": "%(message)s"},
            "precise": {"format": "%(asctime)s <%(levelname)s>: %(message)s"},
            "full": {
                "format": "[%(name)s] %(asctime)s <%(levelname)s>: "
                + "%(message)s"
            },
        },
    }
    log_config["handlers"]["log-file"]["filename"] = str(log_file)
    config.dictConfig(log_config)


# Classes to keep track of status of individual scenes and (possibly
# multiple) runs of those scenes
class StatusEnum(Enum):
    UNKNOWN = auto()
    PENDING = auto()
    RETRYING = auto()
    SUCCESS = auto()
    ERROR = auto()
    ERROR_TIMEOUT = auto()


@dataclass
class RunStatus:
    exit_code: int
    output: str
    status: StatusEnum
    job_id = None
    retry: bool = False


@dataclass
class SceneStatus:
    scene_file: str
    retries: int = 0
    status: StatusEnum = StatusEnum.UNKNOWN
    run_statuses: List[RunStatus] = field(default_factory=list)


class SceneRunner:
    """
    SceneRunner is executed on the Ray head machine and manages the
    execution of all the scenes, including retries.
    """

    # Valid properties for various fields in mcs_config_file
    METADATA_LVLS = ["level1", "level2", "oracle"]
    EVAL_NAMES = [
        "eval_3-75",
        "eval_4",
        "eval_5",
        "eval_6",
        "eval_7",
        "eval_8",
    ]
    TEAM_NAMES = ["mess", "mess1", "mess2", "mit", "opics", "baseline", "cora"]
    #  more flexible for Eval 4+ and update folder structure
    CURRENT_EVAL_BUCKET = "evaluation-images"
    CURRENT_EVAL_FOLDER = "eval-resources-4"
    CURRENT_MOVIE_FOLDER = "raw-eval-4"

    def __init__(self, args):

        # Get Execution Configuration, which has scene information
        # and how to run scripts on the worker machines
        self.exec_config = configparser.ConfigParser()
        self.exec_config.read(args.execution_config_file)
        self.disable_validation = args.disable_validation
        self.resume = args.resume

        # Get MCS configuration, which has information about how to
        # run the MCS code, metadata level, etc.
        self.mcs_config = self.read_mcs_config(args.mcs_config_file)
        self.check_for_valid_mcs_config()

        self.scene_files_list = []

        # Scene_statuses keeps track of all the scenes and current status.
        # Maps job_id to SceneStatus object
        self.scene_statuses = {}

        # List of all the job references that have been submitted to Ray that
        # have not completed.  We call ray.wait on these to get job outputs
        self.not_done_jobs = []

        self.get_scenes()
        self.on_start_scenes()
        self.run_scenes()
        self.on_finish_scenes()
        self.print_results()

    def read_mcs_config(self, mcs_config_filename: str):
        mcs_config = configparser.ConfigParser()
        with open(mcs_config_filename, "r") as mcs_config_file:
            mcs_config.read_file(mcs_config_file)
        return mcs_config

    def check_for_valid_mcs_config(self):
        if self.disable_validation:
            return

        valid = True

        eval = self.mcs_config.getboolean("MCS", "evaluation")
        if not eval:
            logging.error(
                "Error: Evaluation property in MCS "
                + "config file is not set to true."
            )
            valid = False

        video_enabled = self.mcs_config.getboolean("MCS", "video_enabled")
        if not video_enabled:
            logging.error(
                "Error: Video enabled property in MCS "
                + "config file is not set to true."
            )
            valid = False

        history_enabled = self.mcs_config.getboolean("MCS", "history_enabled")
        if not history_enabled:
            logging.error(
                "Error: History enabled property in MCS "
                + "config file is not set to true."
            )
            valid = False

        bucket = self.mcs_config.get("MCS", "s3_bucket")
        if bucket != self.CURRENT_EVAL_BUCKET:
            logging.error(
                "Error: MCS Config file does not have "
                + "the correct s3 bucket specified."
            )
            valid = False

        s3_folder = self.mcs_config.get("MCS", "s3_folder")
        if s3_folder != self.CURRENT_EVAL_FOLDER:
            logging.error(
                "Error: MCS Config file does not have "
                + "the correct s3 folder specified."
            )
            valid = False


        s3_movies_folder = self.mcs_config.get('MCS', 's3_movies_folder')
        if s3_movies_folder != self.CURRENT_MOVIE_FOLDER:
            logging.error('Error: MCS Config file does not have ' +
                  'the correct s3 movies folder specified.')

            valid = False

        metadata = self.mcs_config.get("MCS", "metadata")
        if metadata not in self.METADATA_LVLS:
            logging.error(
                "Error: MCS Config file does not include "
                + "valid metadata level."
            )
            valid = False

        eval_name = self.mcs_config.get("MCS", "evaluation_name")
        if eval_name not in self.EVAL_NAMES:
            logging.error(
                "Error: MCS Config file does not "
                + "include valid evaluation_name."
            )
            valid = False

        team = self.mcs_config.get("MCS", "team")
        if team not in self.TEAM_NAMES:
            logging.error(
                "Error: MCS Config file does not " + "include valid team name."
            )
            valid = False

        # Needed for multiple submissions from MESS
        # TODO: make more generic post eval 4 and incorporate into
        # Python API/ingest (MCS-928)
        submission_id = self.mcs_config.get(
            "MCS", "submission_id", fallback=None
        )
        if (
            team == "mess1"
            and submission_id != "1"
            or team == "mess2"
            and submission_id != "2"
        ):
            logging.error(
                "Error: For MESS submissions, need the "
                + "submission_id to match the team name suffix (1 or 2)."
            )
            valid = False

        logs_to_s3 = self.mcs_config.getboolean(
            "MCS", "logs_to_s3", fallback=True
        )
        if not logs_to_s3:
            logging.error(
                "Error: MCS Config does not have logs_to_s3 enabled."
            )
            valid = False

        if not valid:
            raise Exception(
                "Invalid property value in MCS config file. "
                + "If only testing and not running an eval, "
                + "please use the --disable_validation flag."
            )

    def get_scenes(self):
        """Read the scene files to use from the argument scene_list"""

        base_dir = pathlib.Path(self.exec_config["MCS"]["scene_location"])
        task_file = open(self.exec_config["MCS"]["scene_list"], "r")
        lines = task_file.readlines()
        for line in lines:
            if line is not None and len(line) > 0:
                self.scene_files_list.append(base_dir / line.strip())

        # Filter scene_files_list based on last run file.
        if (
            self.resume
            and pathlib.Path(FINISHED_SCENES_LIST_FILENAME).exists()
        ):
            with open(FINISHED_SCENES_LIST_FILENAME) as last_run_list:
                lines = last_run_list.readlines()
                for line in lines:
                    file = pathlib.Path(line.strip())
                    logging.debug(
                        f"Attempting to remove {line} from file list"
                    )
                    if file in self.scene_files_list:
                        self.scene_files_list.remove(file)

        self.scene_files_list.sort()
        logging.info(f"Number of scenes: {len(self.scene_files_list)}")
        logging.info(f"Scenes {self.scene_files_list}")

    def run_scenes(self):
        logging.info(f"Running {len(self.scene_files_list)} scenes")
        job_ids = []
        run_script = self.exec_config["MCS"]["run_script"]
        eval_dir = self.exec_config["MCS"]["eval_dir"]
        for scene_ref in self.scene_files_list:
            with open(str(scene_ref)) as scene_file:
                job_id = run_scene.remote(
                    run_script,
                    self.mcs_config,
                    json.load(scene_file),
                    eval_dir,
                    1,
                )
                self.scene_statuses[job_id] = SceneStatus(
                    scene_ref, 0, StatusEnum.PENDING
                )
                job_ids.append(job_id)

        self.not_done_jobs = job_ids
        while self.not_done_jobs:
            done_jobs, self.not_done_jobs = ray.wait(self.not_done_jobs)
            for done_ref in done_jobs:
                result, output = ray.get(done_ref)
                scene_status = self.scene_statuses.get(done_ref)
                run_status = self.get_run_status(
                    result, output, scene_status.scene_file
                )
                scene_status.run_statuses.append(run_status)

                logging.info(
                    "Run results for file: " + f"{scene_status.scene_file}"
                )
                self.print_run_status(run_status, "    ")

                if run_status.retry and scene_status.retries < NUM_RETRIES:
                    self.retry_job(scene_status)
                    scene_status.retries += 1
                    scene_status.status = StatusEnum.RETRYING
                    # Remove entry tied to old ray reference (done_ref)
                    self.scene_statuses.pop(done_ref)
                else:
                    # If we are finished, full scene status should be
                    # same as last run status
                    scene_status.status = run_status.status
                    self.on_scene_finished(scene_status)
                self.print_status()

    def print_status(self):
        """During the run, print out the number of completed jobs,
        number current running, number to go, number failed, etc"""
        logging.info(f"Status for {len(self.scene_statuses)} scenes: ")
        current_statuses = [
            scene_status.status
            for scene_status in self.scene_statuses.values()
        ]
        frequency = {
            scene_status: current_statuses.count(scene_status)
            for scene_status in current_statuses
        }

        for key, value in frequency.items():
            logging.info(f"    {key.name} -> {value}")

    def retry_job(self, scene_status: SceneStatus):
        scene_ref = scene_status.scene_file
        with open(str(scene_ref)) as scene_file:
            # Retries is +2 to get test number because +1 for next run
            # increment and +1 for changing to 0 base to 1 base index
            job_id = run_scene.remote(
                self.exec_config["MCS"]["run_script"],
                self.mcs_config,
                json.load(scene_file),
                self.exec_config["MCS"]["eval_dir"],
                scene_status.retries + 2,
            )
            logging.info(f"Retrying {scene_ref} with job_id={job_id}")
            self.scene_statuses[job_id] = scene_status
            self.not_done_jobs.append(job_id)

    def print_results(self):
        # scenes may have multiple entries of they were retried
        scenes_printed = []
        logging.info("Status:")
        for key in self.scene_statuses:
            s_status = self.scene_statuses[key]
            file = s_status.scene_file
            if file not in scenes_printed:
                scenes_printed.append(file)
                self.print_scene_status(s_status, "  ")
        self.print_status()

    def print_scene_status(self, s_status, prefix=""):
        logging.info(
            f"{prefix}Scene: {s_status.status} - " + f"'{s_status.scene_file}"
        )
        logging.info(f"{prefix}  retries: {s_status.retries}")
        for x, run in enumerate(s_status.run_statuses):
            logging.info(f"{prefix}  Attempt {x}")
            self.print_run_status(run, "      ")

    def print_run_status(self, run, prefix=""):
        logging.info(f"{prefix}Code: {run.exit_code}")
        logging.info(f"{prefix}Status: {run.status}")
        logging.info(f"{prefix}Retryable: {run.retry}")

    def get_run_status(
        self, result: int, output: str, scene_file_path: str
    ) -> RunStatus:
        status = RunStatus(result, output, StatusEnum.SUCCESS, False)
        if result != 0:
            status.retry |= False
            status.status = StatusEnum.ERROR
        if "Exception in create_controller() Time out!" in output:
            logging.info(f"Timeout occured for file={scene_file_path}")
            status.retry |= True
            status.status = StatusEnum.ERROR_TIMEOUT
        # Add more conditions to retry here
        return status

    def on_start_scenes(self):
        # for stop and restart
        finished_scenes_filename = pathlib.Path(FINISHED_SCENES_LIST_FILENAME)
        # we added self.resume check because if we are resuming, we want that
        # previous list to stay.  Those are already completed successfully
        if finished_scenes_filename.exists() and not self.resume:
            finished_scenes_filename.unlink()
        self.finished_scenes_file = open(str(finished_scenes_filename), "a")

    def on_scene_finished(self, status: SceneStatus):
        self.finished_scenes_file.write(f"{status.scene_file}\n")
        self.finished_scenes_file.flush()

    def on_finish_scenes(self):
        # For stop and restart
        finished_scenes_filename = pathlib.Path(FINISHED_SCENES_LIST_FILENAME)
        if finished_scenes_filename.exists():
            finished_scenes_filename.unlink()


def parse_args():
    parser = argparse.ArgumentParser(description="Run scenes using ray")
    parser.add_argument(
        "execution_config_file",
        help="Ini file that describes scenes and "
        + "what script to run for a performer",
    )
    parser.add_argument(
        "mcs_config_file",
        help="Ini file that describes MCS configuration, "
        + "debug, metadata, team, etc. ",
    )
    parser.add_argument(
        "--disable_validation",
        default=False,
        action="store_true",
        help="Whether or not to skip validatation of MCS config file",
    )
    parser.add_argument(
        "--resume",
        default=False,
        action="store_true",
        help="Whether to attempt to resume last run.",
    )
    parser.add_argument(
        "--local_only",
        default=False,
        action="store_true",
        help="Whether or not one is running on a local machine "
        + "or on a remote cluster",
    )

    return parser.parse_args()


def format_datetime(time_obj):
    """Format a time (from time.time() in format like: 2021-07-13 13:01:35"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_obj))


def show_datetime_string(prefix: str = ""):
    now_time = time.time()
    date_str = format_datetime(now_time)
    logging.info(f"{prefix}{date_str}")
    return now_time


if __name__ == "__main__":
    args = parse_args()

    start_time = show_datetime_string("Start time: ")

    # Note that logging_level is set to logging.INFO by default
    # in ray.init() call (in case we need to change logging levels)
    if args.local_only:
        ray.init(local_mode=True)
    else:
        ray.init(address="auto")

    try:
        scene_runner = SceneRunner(args)
    except Exception as e:
        logging.info("Exception: ", exc_info=e)

    # Give it time to wrap up, produce output from the ray workers
    time.sleep(2)

    end_time = show_datetime_string("End time: ")

    elapsed_sec = end_time - start_time
    logging.info(f"Elapsed: {elapsed_sec} sec")

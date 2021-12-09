import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import copy
import pathlib
import subprocess
import sys
from typing import Dict, List, Union

import pathlib
import yaml
import os
import threading
import queue
import time
import random

# TODO:
# update after all teams eval4 is merged
# make sure parameters get pass through (disable_validation, dev, resume, etc)
#   update dev
# make template location configurable


from configparser import ConfigParser

from mako.template import Template

DEFAULT_VARSET = 'default'
RAY_WORKING_DIR = pathlib.Path('./.tmp_pipeline_ray/')
SCENE_LIST_FILENAME = "scenes_single_scene.txt"
DATE_FORMAT = '%Y%m%d-%H%M%S'


@dataclass
class EvalGroupsStatus():
    total_groups: int
    total_scenes: int
    finished_groups: int = 0
    finished_scenes: int = 0

    def __post_init__(self):
        self._start = datetime.now()

    def get_progress_string(self):
        fg = self.finished_groups
        fs = self.finished_scenes
        tg = self.total_groups
        ts = self.total_scenes
        gp = '{:.1%}'.format(fg/tg)
        sp = '{:.1%}'.format(fs/ts)
        return f"Groups: {fg}/{tg} ({gp}%) - scenes: {fs}/{ts} ({sp}%)"

    def get_timing_string(self):
        elapsed = datetime.now() - self._start
        scenes_left = self.total_scenes - self.finished_scenes
        if self.finished_scenes == 0:
            sec_per_scene = "unknown"
            time_left = "unknown"
        else:
            sec_per_scene = elapsed / self.finished_scenes
            time_left = scenes_left * sec_per_scene
        return f"Elapsed: {elapsed} seconds per scene: {sec_per_scene} time left: {time_left}"


@dataclass
class EvalRunStatus():
    total_scenes: int
    success_scenes: int = 0
    failed_scenes: int = 0


@dataclass
class EvalParams:
    varset: List[str]
    scene_dir: str
    metadata: str = "level2"
    override: dict = field(default_factory=dict)
    stats: EvalRunStatus = None


class LogTailer():
    """Reads a log file as it is written"""
    # based off code and comments from
    # https://stackoverflow.com/questions/12523044/how-can-i-tail-a-log-file-in-python
    _file = None
    _terminate = False
    _thread = None

    def __init__(self, file, log_prefix=""):
        self._file = file
        self._log_prefix = log_prefix

    def stop(self):
        """Will stop the tailing and end the thread if non-blocking"""
        self._terminate = True
        if self._thread:
            self._thread.join()

    def tail_non_blocking(self):
        """Tails a file without blocking by using a thread.  Can only be called one per instance."""
        if not self._thread:
            self._terminate = False
            self._thread = threading.Thread(
                target=self.tail_blocking, daemon=True, name=f"tail-{self._file}-{self._log_prefix}")
            self._thread.start()

    def tail_blocking(self):
        """Tails a file by blocking the calling thread."""
        for line in self._get_tail_lines(self._file):
            # sys.stdout.write works better with new lines
            sys.stdout.write(f"{self._log_prefix}{line}")

    def _get_tail_lines(self, file):
        with open(file, 'r') as f:
            while True:
                line = f.readline()
                if line:
                    yield line
                elif self._terminate:
                    break
                else:
                    time.sleep(0.1)


def get_now_str() -> str:
    """Returns a date as a string in a sortable format."""
    return datetime.now().strftime(DATE_FORMAT)


def add_variable_sets(varsets):
    if DEFAULT_VARSET not in varsets:
        varsets.insert(0, DEFAULT_VARSET)
    vars = {}
    for varset in varsets:
        with open(f'mako/variables/{varset}.yaml') as def_file:
            new_vars = yaml.safe_load(def_file)
            vars = {**vars, **new_vars}
    return vars


def execute_shell(cmd, log_file=None):
    # By passing all the commands into this function, the method of
    # executing the shell can easily be changed later.  This could be useful
    # if we want to capture the logging.
    cmd = f"unbuffer {cmd} 2>&1 | ts -S"
    if (log_file):
        with open(log_file, "a") as f:
            subprocess.run([cmd, "|", "ts"], stdout=f,
                           stderr=subprocess.STDOUT, shell=True)
    else:
        subprocess.run(cmd, shell=True)


class RayJobRunner():
    _config_file = None
    _log_file = None

    def __init__(self, config_file: pathlib.Path, log_file=None) -> None:
        self._log_file = log_file
        if not isinstance(config_file, pathlib.Path):
            self._config_file = pathlib.Path(config_file)
        else:
            self._config_file = config_file

    def up(self):
        cmd = f'ray up -y {self._config_file.as_posix()}'
        execute_shell(cmd, self._log_file)

    def rsync_up(self, source, dest):
        execute_shell(
            f"ray rsync_up -v {self._config_file.as_posix()} {source} '{dest}'", self._log_file)

    def exec(self, cmd):
        execute_shell(
            f'ray exec {self._config_file.as_posix()} "{cmd}"', self._log_file)

    def submit(self, file, *args):
        params = " ".join(args)
        execute_shell(
            f"ray submit {self._config_file.as_posix()} {file} {params}",
            self._log_file)


def run_eval(varset, local_scene_dir, metadata="level2", disable_validation=False,
             dev_validation=False, resume=False, override_params={},
             log_file=None, cluster="", output_logs=False, dry_run=False) -> pathlib.Path:
    """Runs an eval and returns the ray config file as a pathlib.Path object."""
    # Get Variables
    vars = add_variable_sets(varset)
    vars = {**vars, **override_params}
    vars['metadata'] = metadata

    # Setup Tail
    if log_file and output_logs:
        lt = LogTailer(log_file, f"c{cluster}: ")
        lt.tail_non_blocking()

    # Setup working directory
    now = get_now_str()
    team = vars['team']
    suffix = f"-{cluster}" if cluster else ""
    working_name = f"{now}-{team}{suffix}"
    RAY_WORKING_DIR.mkdir(exist_ok=True, parents=True)
    working = (RAY_WORKING_DIR / working_name)
    working.mkdir()
    scene_list_file = working/SCENE_LIST_FILENAME

    ray_locations_config = f"configs/{team}_aws.ini"

    # Generate Ray Config
    ray_cfg_template = Template(
        filename='mako/templates/ray_template_aws.yaml')

    ray_cfg = ray_cfg_template.render(**vars)
    ray_cfg_file = working / f"ray_{team}_aws.yaml"
    ray_cfg_file.write_text(ray_cfg)

    # Generate MCS config
    mcs_cfg_template = Template(
        filename='mako/templates/mcs_config_template.ini')
    mcs_cfg = mcs_cfg_template.render(**vars)
    mcs_cfg_file = working / f"mcs_config_{team}_{metadata}.ini"
    mcs_cfg_file.write_text(mcs_cfg)

    # Find and read Ray locations config file
    # source aws_scripts/load_ini.sh $RAY_LOCATIONS_CONFIG
    parser = ConfigParser()
    parser.read(ray_locations_config)
    remote_scene_location = parser.get("MCS", "scene_location")
    remote_scene_list = parser.get("MCS", "scene_list")

    # Create list of scene files
    files = os.listdir(local_scene_dir)
    with open(scene_list_file, 'w') as scene_list_writer:
        for file in files:
            if os.path.isfile(os.path.join(local_scene_dir, file)):
                scene_list_writer.write(file)
                scene_list_writer.write('\n')
        scene_list_writer.close()

    if dry_run:
        # currently we need to sleep just so the timestamp isn't the same
        execute_shell("sleep 2", log_file=log_file)
    else:

        # Start Ray and run ray commands
        ray = RayJobRunner(ray_cfg_file, log_file=log_file)
        # Create config file
        # metadata level
        ray.up()

        ray.rsync_up("pipeline", '~')
        ray.rsync_up(f"deploy_files/{team}/", '~')
        ray.rsync_up("configs/", '~/configs/')
        ray.rsync_up(mcs_cfg_file.as_posix(), '~/configs/')

        ray.exec(f"mkdir -p {remote_scene_location}")

        ray.rsync_up(f"{local_scene_dir}/", remote_scene_location)
        ray.rsync_up(scene_list_file.as_posix(), remote_scene_list)

        submit_params = "--disable_validation" if disable_validation else ""
        submit_params += " --resume" if resume else ""
        submit_params += " --dev" if dev_validation else ""

        remote_cfg_path = f"configs/{mcs_cfg_file.name}"
        ray.submit("pipeline_ray.py", ray_locations_config,
                   remote_cfg_path, submit_params)

    if log_file and output_logs:
        lt.stop()

    return ray_cfg_file


def create_eval_set_from_folder(varset: List[str], base_dir: str, metadata: str = "level2", override: dict = {}):
    eval_set = []
    dirs = os.listdir(base_dir)
    for dir in dirs:
        my_override = copy.deepcopy(override)
        scene_dir = os.path.join(base_dir, dir)
        if os.path.isdir(scene_dir):
            my_override["log_name"] = f"{dir}-{metadata}.log"
            eval_set.append(EvalParams(varset, scene_dir,
                            metadata=metadata, override=my_override))
    return eval_set


def set_status_for_set(eval_set):
    num_scenes = 0
    for eval_run in eval_set:
        dir = eval_run.scene_dir
        run_scenes = len([name for name in os.listdir(dir)
                          if name.endswith('.json') and os.path.isfile(os.path.join(dir, name))])
        num_scenes += run_scenes
        eval_run.stats = EvalRunStatus(run_scenes)
    return EvalGroupsStatus(len(eval_set), num_scenes)


def run_evals(eval_set: List[EvalParams], num_clusters=3, dev=False,
              disable_validation=False, output_logs=False, dry_run=False):
    q = queue.Queue()
    for eval in eval_set:
        q.put(eval)

    all_status = set_status_for_set(eval_set)

    def run_eval_from_queue(num, dev=False):
        log_dir_path = "logs-test"
        log_dir = pathlib.Path(log_dir_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        last_config_file = None
        while(not q.empty()):
            eval = q.get()
            override = eval.override
            override["clusterSuffix"] = f"-{num}"
            print(
                f"Starting eval from {eval.scene_dir} at {eval.metadata} in cluster {num}")
            log_file_name = override.get("log_name")
            if log_file_name:
                log_file = log_dir / pathlib.Path(log_file_name)
                log_file.unlink(missing_ok=True)
            execute_shell("echo Starting `date`", log_file)
            last_config_file = run_eval(eval.varset, eval.scene_dir, eval.metadata,
                                        override_params=eval.override, log_file=log_file,
                                        cluster=num, disable_validation=disable_validation,
                                        dev_validation=dev, output_logs=output_logs, dry_run=dry_run)
            all_status.finished_groups += 1
            all_status.finished_scenes += eval.stats.total_scenes
            execute_shell("echo Finishing `date`", log_file)
            print(
                f"Finished eval from {eval.scene_dir} at {eval.metadata} in cluster {num}")
            print(f"  {all_status.get_progress_string()}")
            print(f"  {all_status.get_timing_string()}")
        print(f"Finished with cluster {num}")
        execute_shell(f"ray down -y {last_config_file.as_posix()}", log_file)

    threads = []
    for i in range(num_clusters):
        t = threading.Thread(target=run_eval_from_queue, args=((i+1), dev))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


def force_array(val):
    """Returns val if it is an array, otherwise a one element array containing val"""
    return val if isinstance(val, list) else [val]


def get_array(group, base, field):
    """
    Returns the value of the field with 'group' values taking precedence 
    over 'base' values

    All returns are forced to an array if not already an array.  
    Returns the field from group. If it doesn't exist, returns the 
    field from base.  If it still doesn't exist, return an empty array."""
    return force_array(group.get(field, base.get(field, [])))


def create_eval_set_from_file(cfg_file: str):
    with open(cfg_file, 'r') as reader:
        cfg = yaml.safe_load(reader)

    base = cfg.get('base', {})

    eval_groups = force_array(cfg.get('eval-groups', []))

    evals = []

    for group in eval_groups:
        my_base = copy.deepcopy(base)
        varset = get_array(group, my_base, 'varset')
        metadata_list = get_array(group, my_base, 'metadata')
        for metadata in metadata_list:
            parents = get_array(group, my_base, 'parent-dir')
            dirs = get_array(group, my_base, 'dirs')
            for dir in dirs:
                log_dir = dir.split("/")[-1]
                my_override = {}
                my_override["log_name"] = f"{log_dir}-{metadata}.log"
                evals.append(EvalParams(
                    varset, dir, metadata, override=my_override))
            for parent in parents:
                new_evals = create_eval_set_from_folder(
                    varset, parent, metadata)
                evals += new_evals
    return evals


def run_from_config_file(args):
    test_set = create_eval_set_from_file(args.config_file)
    run_evals(test_set, dev=args.dev_validation,
              disable_validation=args.disable_validation,
              num_clusters=args.num_clusters, output_logs=args.redirect_logs,
              dry_run=args.dry_run)


def multi_test():
    varset = ['opics', 'kdrumm']
    metadata = 'level2'
    base_dir = 'eval4/split'
    test_set = create_eval_set_from_folder(varset, base_dir, metadata)

    run_evals(test_set)


def single_test():

    varset = ['opics', 'kdrumm']
    metadata = 'level2'
    local_scene_dir = 'eval4/single'

    run_eval(varset, local_scene_dir,
             metadata=metadata, disable_validation=True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run multiple eval sets containing scenes using ray.  There are two modes.  " +
        "One uses the '--config_file' option.  The other uses the '--local_scene_dir' option.")
    parser.add_argument(
        "--config_file", "-c",
        help="Path to config file which contains details on how exactly to run a series of eval runs."
        + "for the eval files to run.",
    )
    parser.add_argument(
        "--dev_validation", "-d",
        default=False,
        action="store_true",
        help="Whether or not to validate for development instead of production",
    )
    parser.add_argument(
        "--disable_validation",
        default=False,
        action="store_true",
        help="Whether or not to skip validatation of MCS config file",
    )
    parser.add_argument(
        "--dry_run",
        default=False,
        action="store_true",
        help="If set, do not actually run anything in ray.  Just creates and parses config files.",
    )
    parser.add_argument(
        "--redirect_logs", "-r",
        default=False,
        action="store_true",
        help="Whether or not to copy output logs to stdout",
    )
    parser.add_argument(
        "--num_clusters", "-n",
        type=int,
        default=1,
        help="How many simultanous clusters should be used.  Only used with the '--config_file' option.",
    )
    parser.add_argument(
        "--local_scene_dir", "-s",
        default=None,
        help="Local scene directory to be used for a single run.  Cannot be used with the '--config_file' option.",
    )
    parser.add_argument(
        "--metadata", "-m",
        default='level2',
        help="Sets the metadata level for a single run.  Only used with the '--local_scene_dir' option.",
    )
    parser.add_argument(
        "--varset", "-v",
        help="Sets list of variable set files that should be read.  Only used with the '--local_scene_dir' option.",
    )
    return parser.parse_args()

    """
    Config File API (yaml):
    The job of this script is to create a list of 'eval-group' parameters which is a set of parameters
    to run a single ray job for an eval.  The parameters for an eval group are below, but in general it is
    used to generate set of files, at a certain metadata level, with some other run parameters.
    To do this, we use a config file to generate these eval groups, where most values are lists where each entry
    is a single option.  The script will create eval-groups using each combination of options to create many 
    permutation of these values.
    
    The config file has two high level objects:
    base - an 'eval-group' object that contains default values for any listed 'eval-groups'.  
    eval-groups - contains a list of 'eval-group' objects.  Each grouping will create a number of sets as described below.
    
    An eval-group is a group of values used to create all permutations of eval sets.  
    Eval sets are parameters and scenes to run a single task in ray for an eval.
    
    values for an eval-group:
      varset - list of variable files that are used for template generation.  Earlier 
        files are override by later values if they contain the same variable.  This is 
        the only array where all values are used for each eval-set instead of each 
        value creating more permutations.  Varset in the 'eval-groups' will override, not 
        concatentate, those in the 'base' variable.
      metadata - single or list of metadata levels.  Each metadata level will create more 
        permutations of the eval-sets
      parent-dir - Must be used mutually exclusively with 'dirs'.   This points to a directory
        where each subdirectory should contain scenes and will be used to create permutations
        of eval-sets
      dirs - Must be used mutually exclusively with 'parent-dir'.  Single or list of directories 
        which each should contain scenes to be used to create permutations of eval-sets.
    
    
    Example:
    base:
        varset: ['opics', 'kdrumm']
    eval-groups:
        - metadata: ['level1', 'level2']
          parent-dir: 'mako-test/parent'
        - metadata: ['level2', 'oracle']
          dirs: ['mako-test/dirs/dir1', 'mako-test/dirs/dir2']
          
    This example will use the 'opics.yaml' and 'kdrumm.yaml' files in the 'variables' directory to fill the templates.
    It will level1 and level2 test using
    """


if __name__ == "__main__":
    args = parse_args()
    if args.config_file:
        run_from_config_file(args)
    elif args.local_scene_dir and args.varset:
        now = get_now_str()
        vars = "-".join(args.varset)
        log_file = f"logs/{now}-{vars}-{args.metadata}.log"
        run_eval(args.varset, args.local_scene_dir,
                 metadata=args.metadata, disable_validation=args.disable_validation,
                 dev_validation=args.dev_validation,
                 resume=args.resume, log_file=log_file, output_logs=args.redirect_logs)

import argparse
import copy
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time
import traceback
from configparser import ConfigParser
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import yaml
from mako.template import Template

DEFAULT_VARSET = 'default'
USER_VARSET = 'user'
RAY_WORKING_DIR = pathlib.Path('./.tmp_pipeline_ray/')
SCENE_LIST_FILENAME = "scenes_single_scene.txt"
DATE_FORMAT = '%Y%m%d-%H%M%S'
RESUME_SAVE_PERIOD_SECONDS = 5*60
STATUS_PRINT_PERIOD_SECONDS = 30


@dataclass
class EvalRunStatus:
    total_scenes: int
    success_scenes: int = 0
    failed_scenes: int = 0
    files: dict = field(default_factory=dict)


@dataclass
class EvalParams:
    varset: List[str]
    scene_dir: str
    metadata: str = "level2"
    override: dict = field(default_factory=dict)
    status: EvalRunStatus = None
    file_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        try:
            self.varset.remove("default")
        except:
            pass

    def get_key(self):
        varset_str = "-".join(self.varset)
        return f"{self.scene_dir}-{varset_str}-{self.metadata}"

    def get_resume_eval_params(self):
        ep = EvalParams(
            copy.deepcopy(self.varset),
            self.scene_dir,
            self.metadata,
            copy.deepcopy(self.override),
        )
        if self.status:
            file_list = []
            if self.file_names:
                file_list = self.file_names
            else:
                # for _, _, files in os.walk(self.scene_dir ):
                #    file_list.extend(files)
                all = os.listdir(self.scene_dir)
                for file in all:
                    if os.path.isfile(self.scene_dir + "/" + file):
                        file_list.append(file)
            for filename in file_list:
                if (
                    filename not in self.status.files
                    or self.status.files.get(filename, "") != "SUCCESS"
                ):
                    ep.file_names.append(filename)
            if not ep.file_names:
                ep = None
        return ep

    def get_yaml_dict(self):
        """Returns dictionary to write as yaml"""
        # for some reason deep copy fixes a yaml issue
        return {
            "varset": copy.deepcopy(self.varset),
            "metadata": [self.metadata],
            "dirs": [self.scene_dir],
            "override": self.override or {},
            "files": self.file_names or [],
        }


@dataclass
class EvalGroupsStatus:
    total_groups: int
    finished_groups: int = 0
    run_statuses = {}

    def __post_init__(self):
        self._start = datetime.now()

    def update_run_status(self, key: str, run_status: EvalRunStatus):
        self.run_statuses[key] = run_status

    def update_dry_run_status(self, key):
        self.run_statuses[key].success_scenes = self.run_statuses[
            key
        ].total_scenes

    def get_progress_string(self):
        success = 0
        failed = 0
        total = 0
        for key in self.run_statuses:
            s = self.run_statuses[key]
            success += s.success_scenes
            failed += s.failed_scenes
            total += s.total_scenes

        fg = self.finished_groups
        fs = success + failed
        tg = self.total_groups
        ts = total
        gp = "{:.1%}".format(fg / tg)
        sp = "{:.1%}".format(fs / ts)
        return f"Groups: {fg}/{tg} ({gp}%) - scenes: {fs}/{ts} ({sp}%)"

    def get_timing_string(self):
        finished = 0
        total = 0
        for key in self.run_statuses:
            s = self.run_statuses[key]
            finished += s.success_scenes
            finished += s.failed_scenes
            total += s.total_scenes
        finished
        elapsed = datetime.now() - self._start
        scenes_left = total - finished
        if finished == 0:
            sec_per_scene = "unknown"
            time_left = "unknown"
        else:
            sec_per_scene = elapsed / finished
            time_left = scenes_left * sec_per_scene
        return f"Elapsed: {elapsed} seconds per scene: {sec_per_scene} time left: {time_left}"


class LogTailer:
    """Reads a log file as it is written"""

    # based off code and comments from
    # https://stackoverflow.com/questions/12523044/how-can-i-tail-a-log-file-in-python
    _file = None
    _terminate = False
    _thread = None
    _triggers = []

    def __init__(self, file, log_prefix="", print_logs=False, id=""):
        self._triggers = []
        self._file = file
        self._log_prefix = log_prefix
        self._print_logs = print_logs
        self._id = f"{id}-" if id else ""

    def add_trigger(self, trigger_str, callback):
        self._triggers.append((trigger_str, callback))

    def _check_triggers(self, line):
        if not isinstance(line, str):
            return
        for trigger in self._triggers:
            try:
                if trigger[0] in line:
                    trigger[1](line)
            except:
                print(f"Failed to run trigger: {trigger}")
                traceback.print_exc()

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
                target=self.tail_blocking,
                daemon=True,
                name=f"tail-{self._id}{self._file}",
            )
            self._thread.start()

    def tail_blocking(self):
        """Tails a file by blocking the calling thread."""
        for line in self._get_tail_lines(self._file):
            # sys.stdout.write works better with new lines
            self._check_triggers(line)
            if self._print_logs:
                sys.stdout.write(f"{self._log_prefix}{line}")

    def _get_tail_lines(self, file):
        with open(file, "r") as f:
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


def add_variable_sets(varsets, varset_directory):
    varsets = copy.deepcopy(varsets)

    vars = {}
    if USER_VARSET not in varsets and os.path.exists(f'{varset_directory}{USER_VARSET}.yaml'):
        varsets.insert(0, USER_VARSET)
    if DEFAULT_VARSET not in varsets:
        varsets.insert(0, DEFAULT_VARSET)
    for varset in varsets:
        with open(f"{varset_directory}{varset}.yaml") as def_file:
            new_vars = yaml.safe_load(def_file)
            vars = {**vars, **new_vars}
    return vars


def execute_shell(cmd, log_file=None):
    # By passing all the commands into this function, the method of
    # executing the shell can easily be changed later.  This could be useful
    # if we want to capture the logging.
    cmd = f"unbuffer {cmd} 2>&1 | ts -S"
    if log_file:
        with open(log_file, "a") as f:
            subprocess.run(
                [cmd, "|", "ts"], stdout=f, stderr=subprocess.STDOUT, shell=True
            )
    else:
        subprocess.run(cmd, shell=True)


class RayJobRunner:
    _config_file = None
    _log_file = None

    def __init__(self, config_file: pathlib.Path, log_file=None) -> None:
        self._log_file = log_file
        if not isinstance(config_file, pathlib.Path):
            self._config_file = pathlib.Path(config_file)
        else:
            self._config_file = config_file

    def up(self):
        cmd = f"ray up -y {self._config_file.as_posix()}"
        execute_shell(cmd, self._log_file)

    def rsync_up(self, source, dest):
        execute_shell(
            f"ray rsync_up -v {self._config_file.as_posix()} {source} '{dest}'",
            self._log_file,
        )

    def exec(self, cmd):
        execute_shell(
            f'ray exec {self._config_file.as_posix()} "{cmd}"', self._log_file
        )

    def submit(self, file, *args):
        params = " ".join(args)
        execute_shell(
            f"ray submit {self._config_file.as_posix()} {file} {params}",
            self._log_file,
        )


class EvalRun:
    dry_run = False
    ray_cfg_file = None
    mcs_cfg_file = None
    submit_params = ""
    remote_scene_location = None
    remote_scene_list = None
    scene_list_file = None
    ray_locations_config = None
    team = None
    metadata = "level2"
    local_scene_dir = None
    set_status_holder = None

    def __init__(
        self,
        eval,
        disable_validation=False,
        dev_validation=False,
        log_file=None,
        cluster="",
        output_logs=False,
        dry_run=False,
        base_dir="mako",
        group_working_dir=RAY_WORKING_DIR,
    ) -> pathlib.Path:
        self.eval = eval
        self.status = self.eval.status
        override_params = eval.override
        self.dry_run = dry_run
        self.metadata = eval.metadata
        self.log_file = log_file
        self.local_scene_dir = eval.scene_dir
        varset = eval.varset
        self.key = eval.get_key()

        # Get Variables
        varset_directory = f"{base_dir}/variables/"
        vars = add_variable_sets(varset, varset_directory=varset_directory)
        vars = {**vars, **override_params}
        vars["metadata"] = self.metadata

        # Setup Tail
        if log_file:
            self.log_trailer = LogTailer(
                log_file, f"c{cluster}: ", print_logs=output_logs, id=cluster
            )
            self.log_trailer.add_trigger("JSONSTATUS:", self.parse_status)
            self.log_trailer.tail_non_blocking()

        # Setup working directory
        now = get_now_str()
        team = vars.get("team", "none")
        self.team = team

        suffix = f"-{cluster}" if cluster else ""
        working_name = f"{now}-{team}{suffix}"
        group_working_dir.mkdir(exist_ok=True, parents=True)
        working = group_working_dir / working_name
        working.mkdir()
        self.scene_list_file = working / SCENE_LIST_FILENAME
        self.working_dir = working

        self.ray_locations_config = f"configs/{team}_aws.ini"

        # Generate Ray Config
        ray_cfg_template = Template(
            filename=f"{base_dir}/templates/ray_template_aws.yaml"
        )

        ray_cfg = ray_cfg_template.render(**vars)
        ray_cfg_file = working / f"ray_{team}_aws.yaml"
        ray_cfg_file.write_text(ray_cfg)
        self.ray_cfg_file = ray_cfg_file

        # Generate MCS config
        mcs_cfg_template = Template(
            filename=f"{base_dir}/templates/mcs_config_template.ini"
        )
        mcs_cfg = mcs_cfg_template.render(**vars)
        mcs_cfg_file = working / f"mcs_config_{team}_{self.metadata}.ini"
        mcs_cfg_file.write_text(mcs_cfg)
        self.mcs_cfg_file = mcs_cfg_file

        # Find and read Ray locations config file
        # source aws_scripts/load_ini.sh $RAY_LOCATIONS_CONFIG
        parser = ConfigParser()
        parser.read(self.ray_locations_config)
        self.remote_scene_location = parser.get("MCS", "scene_location")
        self.remote_scene_list = parser.get("MCS", "scene_list")

        # Create list of scene files
        files = os.listdir(self.local_scene_dir)
        with open(self.scene_list_file, "w") as scene_list_writer:
            for file in files:
                # does file exist and is it in the file list (if we have a list)
                if os.path.isfile(
                    os.path.join(self.local_scene_dir, file)
                ) and (not eval.file_names or file in eval.file_names):
                    scene_list_writer.write(file)
                    scene_list_writer.write("\n")
            scene_list_writer.close()

        self.submit_params = (
            "--disable_validation" if disable_validation else ""
        )
        self.submit_params += " --dev" if dev_validation else ""

    def parse_status(self, line):
        json_str = line.split("JSONSTATUS:")[-1]
        status = json.loads(json_str)
        succ = status["Succeeded"]
        fail = status["Failed"]
        total = status["Total"]

        files = {}

        file_statuses = status["statuses"]
        for fs in file_statuses:
            file = fs["scene_file"]
            files[file] = fs["status"]

        self.status.files = files
        self.status.total_scenes = total
        self.status.success_scenes = succ
        self.status.failed_scenes = fail

        complete_percent = "{:.1%}".format((succ + fail) / total)
        sp = "{:.1%}".format(succ / total)
        fp = "{:.1%}".format(fail / total)
        print(
            f"Group Status - {self.local_scene_dir}-{self.metadata}:"
            f"\n  Finished {succ + fail}/{total} ({complete_percent}) "
            f"\n  Success: {succ}/{total} ({sp}) Failed: {fail}/{total} ({fp})"
        )
        (self.working_dir / "status.txt").write_text(json_str)
        if self.status_holder:
            self.status_holder.update_run_status(self.key, self.status)

    def set_status_holder(self, holder):
        self.status_holder = holder

    def run_eval(self):
        """Runs an eval"""
        log_file = self.log_file
        # should probably only run once?
        if self.dry_run:
            # currently we need to sleep just so the timestamp isn't the same
            execute_shell("sleep 2", log_file=log_file)
            if self.status_holder:
                self.status_holder.update_dry_run_status(self.key)

        else:

            # Start Ray and run ray commands
            ray = RayJobRunner(self.ray_cfg_file, log_file=log_file)
            # Create config file
            # metadata level
            ray.up()

            ray.rsync_up("pipeline", "~")
            ray.rsync_up(f"deploy_files/{self.team}/", "~")
            ray.rsync_up("configs/", "~/configs/")
            ray.rsync_up(self.mcs_cfg_file.as_posix(), "~/configs/")

            ray.exec(f"mkdir -p {self.remote_scene_location}")

            ray.rsync_up(f"{self.local_scene_dir}/",
                         self.remote_scene_location)
            ray.rsync_up(
                self.scene_list_file.as_posix(), self.remote_scene_list
            )

            remote_cfg_path = f"configs/{self.mcs_cfg_file.name}"
            ray.submit(
                "ray_scripts/pipeline_ray.py",
                self.ray_locations_config,
                remote_cfg_path,
                self.submit_params,
            )

        if self.log_trailer:
            self.log_trailer.stop()


def create_eval_set_from_folder(
    varset: List[str],
    base_dir: str,
    metadata: str = "level2",
    override: dict = {},
):
    eval_set = []
    dirs = os.listdir(base_dir)
    for dir in dirs:
        my_override = copy.deepcopy(override)
        scene_dir = os.path.join(base_dir, dir)
        if os.path.isdir(scene_dir):
            my_override["log_name"] = f"{dir}-{metadata}.log"
            eval_set.append(
                EvalParams(
                    varset, scene_dir, metadata=metadata, override=my_override
                )
            )
    return eval_set


def set_status_for_set(eval_set):
    num_scenes = 0
    group_status = EvalGroupsStatus(len(eval_set))
    for eval_run in eval_set:
        dir = eval_run.scene_dir
        if eval_run.file_names:
            run_scenes = 0
            for file in eval_run.file_names:
                if os.path.exists(os.path.join(dir, file)):
                    run_scenes += 1
                else:
                    print(
                        f"Failed to find file: {os.path.join(dir, file)}.  Skipping file."
                    )
        else:
            run_scenes = len(
                [
                    name
                    for name in os.listdir(dir)
                    if name.endswith(".json")
                    and os.path.isfile(os.path.join(dir, name))
                ]
            )
        num_scenes += run_scenes
        eval_run.status = EvalRunStatus(run_scenes)
        key = eval_run.get_key()
        group_status.update_run_status(key, eval_run.status)
    return group_status


def print_status_periodically(status: EvalGroupsStatus, periodic_seconds):
    while True:
        time.sleep(periodic_seconds)
        print("Status:")
        print(f"  {status.get_progress_string()}")
        print(f"  {status.get_timing_string()}")


def save_config_periodically(
    eval_set: List[EvalParams], periodic_seconds, working_dir
):
    while True:
        time.sleep(periodic_seconds)
        resumes = [eval.get_resume_eval_params() for eval in eval_set]
        my_list = [eval.get_yaml_dict() for eval in resumes if eval]
        resume_file = working_dir / "resume.yaml"
        with open(resume_file, "w") as file:
            d = {"eval-groups": my_list}
            yaml.dump(d, file)
        print(f"wrote resume file {resume_file.as_posix()}")


def run_evals(
    eval_set: List[EvalParams],
    num_clusters=3,
    dev=False,
    disable_validation=False,
    output_logs=False,
    dry_run=False,
    base_dir="mako",
):
    q = queue.Queue()
    for eval in eval_set:
        q.put(eval)

    group_working_dir = RAY_WORKING_DIR / get_now_str()

    all_status = set_status_for_set(eval_set)

    t = threading.Thread(
        target=print_status_periodically,
        args=(all_status, STATUS_PRINT_PERIOD_SECONDS),
        daemon=True,
        name="status-printer",
    )
    t.start()

    t = threading.Thread(
        target=save_config_periodically,
        args=(eval_set, RESUME_SAVE_PERIOD_SECONDS, group_working_dir),
        daemon=True,
        name="status-saver",
    )
    t.start()

    def run_eval_from_queue(num, dev=False):
        log_dir_path = "logs-test"
        log_dir = pathlib.Path(log_dir_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        last_config_file = None
        while not q.empty():
            eval = q.get()
            override = eval.override
            override["clusterSuffix"] = f"-{num}"
            print(
                f"Starting eval from {eval.scene_dir} at {eval.metadata} in cluster {num}"
            )
            log_file_name = override.get("log_name")
            if log_file_name:
                log_file = log_dir / pathlib.Path(log_file_name)
                log_file.unlink(missing_ok=True)
            execute_shell("echo Starting `date`", log_file)
            eval_run = EvalRun(
                eval,
                log_file=log_file,
                cluster=num,
                disable_validation=disable_validation,
                dev_validation=dev,
                output_logs=output_logs,
                dry_run=dry_run,
                base_dir=base_dir,
                group_working_dir=group_working_dir,
            )
            eval_run.set_status_holder(all_status)

            eval_run.run_eval()
            last_config_file = eval_run.ray_cfg_file
            all_status.finished_groups += 1
            # all_status.finished_scenes += eval.status.total_scenes
            execute_shell("echo Finishing `date`", log_file)
            print(
                f"Finished eval from {eval.scene_dir} at {eval.metadata} in cluster {num}"
            )
            print(f"  {all_status.get_progress_string()}")
            print(f"  {all_status.get_timing_string()}")
        print(f"Finished with cluster {num}")
        execute_shell(f"ray down -y {last_config_file.as_posix()}", log_file)

    threads = []
    for i in range(num_clusters):
        t = threading.Thread(
            target=run_eval_from_queue,
            args=((i + 1), dev),
            name=f"runner-cluster-{i+1}",
        )
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


def create_eval_set_from_file(cfg_file: str, super_override: dict = {}) -> List[EvalParams]:
    """Creates and array of EvalParams to run an eval from a configuration file.  See Readme for details of config file.

    Args:
        cfg_file (str): config file
        super_override (dict, optional): Adds to and overrides override from files. Defaults to {}.

    Returns:
        (list(EvalParams)): List of parameters for eval runs
    """
    with open(cfg_file, "r") as reader:
        cfg = yaml.safe_load(reader)

    base = cfg.get("base", {})

    eval_groups = force_array(cfg.get("eval-groups", []))

    evals = []

    for group in eval_groups:
        my_base = copy.deepcopy(base)
        varset = copy.deepcopy(get_array(group, my_base, "varset"))
        metadata_list = get_array(group, my_base, "metadata")
        override = group.get(field, my_base.get("override", {}))

        # apply super override
        if super_override:
            for key, value in super_override.items():
                override[key] = value

        files = get_array(group, base, "files")
        for metadata in metadata_list:
            parents = get_array(group, my_base, "parent-dir")
            dirs = get_array(group, my_base, "dirs")
            for dir in dirs:
                log_dir = dir.split("/")[-1]
                my_override = copy.deepcopy(override) if override else {}
                my_override["log_name"] = f"{log_dir}-{metadata}.log"
                eval = EvalParams(varset, dir, metadata, override=my_override)
                if files:
                    eval.file_names = files
                evals.append(eval)
            for parent in parents:
                new_evals = create_eval_set_from_folder(
                    varset, parent, metadata, override
                )

                evals += new_evals
    return evals


def _args_to_override(args) -> dict:
    override = {}
    if args.num_workers and args.num_workers > 0:
        override['workers'] = args.num_workers
    if args.cluster_user:
        override['clusterUser'] = f"-{args.cluster_user}"
    return override


def run_from_config_file(args):
    super_override = _args_to_override(args)
    test_set = create_eval_set_from_file(args.config_file, super_override)
    run_evals(
        test_set,
        dev=args.dev_validation,
        disable_validation=args.disable_validation,
        num_clusters=args.num_clusters,
        output_logs=args.redirect_logs,
        dry_run=args.dry_run,
        base_dir=args.base_dir
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run multiple eval sets containing scenes using ray."
    )
    # --config_file is required but still needs tag because varset can have variable parameters

    parser.add_argument(
        "--config_file",
        "-c",
        required=True,
        help="Path to config file which contains details on how exactly to run a series of eval runs."
        + "for the eval files to run.",
    )
    parser.add_argument(
        "--base_dir",
        "-b",
        default="mako",
        help="Base directory that should contain a templates directory and variables directory.",
    )
    parser.add_argument(
        "--dev_validation",
        "-d",
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
        "--redirect_logs",
        "-r",
        default=False,
        action="store_true",
        help="Whether or not to copy output logs to stdout",
    )
    parser.add_argument(
        "--num_clusters",
        "-n",
        type=int,
        default=1,
        help="How many simultanous clusters should be used.",
    )
    parser.add_argument(
        "--num_workers", "-w",
        type=int,
        default=None,
        help="How many simultanous workers for each cluster.  This will override any value in varsets.",
    )
    parser.add_argument(
        "--cluster_user", "-u",
        type=str,
        default=None,
        help="Tags the cluster with a the username provided with this parameter.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_from_config_file(args)

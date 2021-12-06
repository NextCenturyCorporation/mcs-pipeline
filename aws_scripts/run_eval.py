from datetime import datetime
from dataclasses import dataclass, field

import copy
import pathlib
import subprocess
from typing import Dict, List

import pathlib
import yaml
import os
import threading
import queue
import time
import random

from configparser import ConfigParser

from mako.template import Template

DEFAULT_VARSET = 'default'
RAY_WORKING_DIR = pathlib.Path('./.tmp_pipeline_ray/')
SCENE_LIST_FILENAME = "scenes_single_scene.txt"


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
    cmd = f"{cmd} 2>&1 | ts -S"
    if (log_file):
        with open(log_file, "a") as f:
            subprocess.run([cmd, "|", "ts"], stdout=f,
                           stderr=subprocess.STDOUT, shell=True)
    else:
        subprocess.run(cmd, shell=True)

    # os.system(cmd)


def run_eval(varset, local_scene_dir, metadata="level2", disable_validation=False,
             dev_validation=False, resume=False, override_params={}, log_file=None, cluster=""):
    # Get Variables
    vars = add_variable_sets(varset)
    vars = {**vars, **override_params}

    ray_cfg_template = Template(
        filename='mako/templates/ray_template_aws.yaml')

    # Setup working directory
    now = datetime.now().strftime('%Y%m%d-%H%M%S')
    team = vars['team']
    suffix = f"-{cluster}" if cluster else ""
    working_name = f"{now}-{team}{suffix}"
    RAY_WORKING_DIR.mkdir(exist_ok=True, parents=True)
    working = (RAY_WORKING_DIR / working_name)
    working.mkdir()
    scene_list_file = working/SCENE_LIST_FILENAME

    ray_locations_config = f"configs/{team}_aws.ini"

    # Generate Ray Config
    ray_cfg = ray_cfg_template.render(**vars)
    ray_cfg_file = working / f"ray_{team}_aws.yaml"
    ray_cfg_file.write_text(ray_cfg)

    # Create config file
    # metadata level
    cmd = f'ray up -y {ray_cfg_file.as_posix()}'
    execute_shell(cmd, log_file)

    # Ray Start
    # ray up -y $RAY_CONFIG
    # wait

    # We should copy all the pipeline code, but at least opics needs it in a special folder.  Should ray_script handle that?
    # Should we run
    # ray rsync_up -v $RAY_CONFIG pipeline '~'
    # ray rsync_up -v $RAY_CONFIG deploy_files/${MODULE}/ '~'
    # ray rsync_up -v $RAY_CONFIG configs/ '~/configs/'
    execute_shell(
        f"ray rsync_up -v {ray_cfg_file.as_posix()} pipeline '~'", log_file)
    execute_shell(
        f"ray rsync_up -v {ray_cfg_file.as_posix()} deploy_files/{team}/ '~'", log_file)
    execute_shell(
        f"ray rsync_up -v {ray_cfg_file.as_posix()} configs/ '~/configs/'", log_file)

    # Find and read Ray locations config file
    # source aws_scripts/load_ini.sh $RAY_LOCATIONS_CONFIG
    parser = ConfigParser()
    parser.read(ray_locations_config)
    remote_scene_location = parser.get("MCS", "scene_location")
    remote_scene_list = parser.get("MCS", "scene_list")

    mcs_config = f"configs/mcs_config_{team}_{metadata}.ini"

    # Create list of scene files
    files = os.listdir(local_scene_dir)
    with open(scene_list_file, 'w') as scene_list_writer:
        for file in files:
            if os.path.isfile(os.path.join(local_scene_dir, file)):
                scene_list_writer.write(file)
                scene_list_writer.write('\n')
        scene_list_writer.close()

    # ray exec $RAY_CONFIG "mkdir -p $MCS_scene_location"
    execute_shell(
        f'ray exec {ray_cfg_file.as_posix()} "mkdir -p {remote_scene_location}"', log_file)

    # this may cause re-used machines to have more scenes than necessary in the follow location.
    # I believe this is ok since we use the txt file to control exactly which files are run.

    # ray rsync_up -v $RAY_CONFIG $LOCAL_SCENE_DIR/ "$MCS_scene_location"
    # ray rsync_up -v $RAY_CONFIG $TMP_DIR/scenes_single_scene.txt "$MCS_scene_list"
    execute_shell(
        f'ray rsync_up -v {ray_cfg_file.as_posix()} '
        f'{local_scene_dir}/ "{remote_scene_location}"', log_file)
    execute_shell(
        f'ray rsync_up -v {ray_cfg_file.as_posix()} '
        f'{scene_list_file.as_posix()} "{remote_scene_list}"', log_file)

    submit_params = "--disable_validation" if disable_validation else ""
    submit_params += " --resume" if resume else ""
    submit_params += " --dev" if dev_validation else ""

    # ray submit $RAY_CONFIG pipeline_ray.py $RAY_LOCATIONS_CONFIG $MCS_CONFIG $SUBMIT_PARAMS
    execute_shell(
        f"ray submit {ray_cfg_file.as_posix()} pipeline_ray.py "
        f"{ray_locations_config} {mcs_config} {submit_params}", log_file)


@dataclass
class EvalParams:
    varset: List[str]
    scene_dir: str
    metadata: str = "level2"
    override: dict = field(default_factory=dict)


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


def run_evals(eval_set: List[EvalParams], num_clusters=3, dev=False):
    q = queue.Queue()
    for eval in eval_set:
        q.put(eval)

    def run_eval_from_queue(num, dev=False):
        log_dir_path = "logs-test"
        log_dir = pathlib.Path(log_dir_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        while(not q.empty()):
            eval = q.get()
            override = eval.override
            override["clusterSuffix"] = f"-{num}"
            print(f"Starting eval from {eval.scene_dir} in cluster {num}")

            log_file_name = override.get("log_name")
            if log_file_name:
                log_file = log_dir / pathlib.Path(log_file_name)
                log_file.unlink(missing_ok=True)
            execute_shell("echo Starting `date`", log_file)
            #TODO need to change dev flag to dev validation once dev validation is merged in
            run_eval(eval.varset, eval.scene_dir, eval.metadata,
                     override_params=eval.override, log_file=log_file, cluster=num, disable_validation = dev)
            execute_shell("echo Finishing `date`", log_file)
            print(f"Finished eval from {eval.scene_dir} in cluster {num}")
        print(f"Finished with cluster {num}")

    threads = []
    for i in range(num_clusters):
        t = threading.Thread(target=run_eval_from_queue, args=((i+1), dev))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


def force_array(val):
    return val if isinstance(val, list) else [val]


def get_array(group, base, field):
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
                my_override = {}
                log_dir = dir.split("/")[-1]
                my_override["log_name"] = f"{log_dir}-{metadata}.log"
                evals.append(EvalParams(
                    varset, dir, metadata, override=my_override))
            for parent in parents:
                new_evals = create_eval_set_from_folder(
                    varset, parent, metadata)
                evals += new_evals
    return evals


def file_test():
    cfg_file = "mako/eval.yaml"
    test_set = create_eval_set_from_file(cfg_file)

    run_evals(test_set, dev=True)


def multi_test():
    varset = ['opics', 'kdrumm']
    metadata = 'level2'
    base_dir = 'eval4/split'
    test_set = create_eval_set_from_folder(varset, base_dir, metadata)
    # TODO allow test_sets be created in files

    run_evals(test_set)


def single_test():

    varset = ['opics', 'kdrumm']
    metadata = 'level2'
    local_scene_dir = 'eval4/single'

    run_eval(varset, local_scene_dir,
             metadata=metadata, disable_validation=True)


if __name__ == "__main__":
    # args = parse_args()
    file_test()

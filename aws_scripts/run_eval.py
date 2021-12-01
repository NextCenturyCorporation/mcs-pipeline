from datetime import datetime
import pathlib

import yaml
import os

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


def execute_shell(cmd):
    # By passing all the commands into this function, the method of
    # executing the shell can easily be changed later.  This could be useful
    # if we want to capture the logging.
    os.system(cmd)


def run_eval(varset, local_scene_dir, metadata="level2", disable_validation=False,
             dev_validation=False, resume=False, override_params={}):
    # Get Variables
    vars = add_variable_sets(varset)
    vars = {**vars, **override_params}

    # Setup working directory
    now = datetime.now().strftime('%Y%m%d-%H%M%S')
    team = vars['team']
    working_name = f"{now}-{team}"
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
    execute_shell(cmd)

    # Ray Start
    # ray up -y $RAY_CONFIG
    # wait

    # We should copy all the pipeline code, but at least opics needs it in a special folder.  Should ray_script handle that?
    # Should we run
    # ray rsync_up -v $RAY_CONFIG pipeline '~'
    # ray rsync_up -v $RAY_CONFIG deploy_files/${MODULE}/ '~'
    # ray rsync_up -v $RAY_CONFIG configs/ '~/configs/'
    execute_shell(f"ray rsync_up -v {ray_cfg_file.as_posix()} pipeline '~'")
    execute_shell(
        f"ray rsync_up -v {ray_cfg_file.as_posix()} deploy_files/{team}/ '~'")
    execute_shell(
        f"ray rsync_up -v {ray_cfg_file.as_posix()} configs/ '~/configs/'")

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
        f'ray exec {ray_cfg_file.as_posix()} "mkdir -p {remote_scene_location}"')

    # this may cause re-used machines to have more scenes than necessary in the follow location.
    # I believe this is ok since we use the txt file to control exactly which files are run.

    # ray rsync_up -v $RAY_CONFIG $LOCAL_SCENE_DIR/ "$MCS_scene_location"
    # ray rsync_up -v $RAY_CONFIG $TMP_DIR/scenes_single_scene.txt "$MCS_scene_list"
    execute_shell(
        f'ray rsync_up -v {ray_cfg_file.as_posix()} '
        f'{local_scene_dir}/ "{remote_scene_location}"')
    execute_shell(
        f'ray rsync_up -v {ray_cfg_file.as_posix()} '
        f'{scene_list_file.as_posix()} "{remote_scene_list}"')

    submit_params = "--disable_validation" if disable_validation else ""
    submit_params += " --resume" if resume else ""
    submit_params += " --dev" if dev_validation else ""

    # ray submit $RAY_CONFIG pipeline_ray.py $RAY_LOCATIONS_CONFIG $MCS_CONFIG $SUBMIT_PARAMS
    execute_shell(
        f"ray submit {ray_cfg_file.as_posix()} pipeline_ray.py "
        f"{ray_locations_config} {mcs_config} {submit_params}")


if __name__ == "__main__":
    # args = parse_args()

    ray_cfg_template = Template(
        filename='mako/templates/ray_template_aws.yaml')

    varset = ['opics', 'kdrumm']
    metadata = 'level2'
    local_scene_dir = 'eval4/single'

    run_eval(varset, local_scene_dir,
             metadata=metadata, disable_validation=True)

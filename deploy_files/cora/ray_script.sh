#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "Running CORA with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh
export DISPLAY=:0

# Clear out directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:

# Adjust for where they hardcoded the scene file to be read from, might be different next collab/evaluation run
cd "$eval_dir"/assets/scene_jsons/test_scenes_small || exit
rm ./*
cp "$scene_file" .
# End Adjust

cd "$eval_dir" || exit
source /home/ubuntu/CoraAgent/venv/bin/activate && julia --project /home/ubuntu/CoraAgent/test_drafts/test_submission.jl "$scene_file"

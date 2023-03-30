#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "Running CORA with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Clear out directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:


# Adjust for where they hardcoded the scene file to be read from, might be different next collab/evaluation run
echo "Copy Scene Files:"

mkdir /home/ubuntu/scenes/caci
cd /home/ubuntu/scenes/caci/ || exit
rm ./*
cp "$scene_file" .
# End Adjust

echo $(basename "$scene_file")

cd "$eval_dir" || exit

# Start X
source /home/ubuntu/start_x_server.sh

export DISPLAY=:4

## Running the Scene. You can run this in a separate shell/tmux sessions or in the same shell too
cd /home/ubuntu/CoraAgent || exit
DISPLAY=:4 julia --project test/runtests.jl /home/ubuntu/scenes/caci/
jobs
echo "Completed Evaluation of Scene:" "$scene_file" 
exit 0
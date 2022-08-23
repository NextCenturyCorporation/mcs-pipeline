#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154
SCENE_DIR="$eval_dir/scenes/"

# shellcheck disable=SC2154
echo "Running MESS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*
echo Clearing "$SCENE_DIR"
rm -rf "${SCENE_DIR:?}"/*

# Move files to appropriate locations
echo Making SCENE_DIR="$SCENE_DIR"
mkdir -p "$SCENE_DIR"
echo Moving scene_file="$scene_file" to "$SCENE_DIR"
cp "$scene_file" "$SCENE_DIR"/

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Go to the mess_eval4/, which is where we will be running things
cd "$eval_dir" || exit

# Activate conda environment
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate mess5

# if DISPLAY environment variable is set in their environment,
# unset it - they are setup a little differently and use vncserver
# instead
unset DISPLAY

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename "$scene_file")

# For eval 4, MESS only gave one submission -- commenting out multi
# submission bits from eval 3.75...

# Read in which submission to run from MCS config file
#SUBMISSION_ID=$(awk -F '=' '/submission_id/ {print $2}' $mcs_configfile | xargs)

# echo Running script_mess.py submission $SUBMISSION_ID

# run with SUBMISSION_ID set to '1' or '2' for both MESS submissions
#python3 script_mess.py scenes/$scene_file_basename $SUBMISSION_ID

python src/script_mess_clean.py scenes/"$scene_file_basename"

unset MCS_CONFIG_FILE_PATH

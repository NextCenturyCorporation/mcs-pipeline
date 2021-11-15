#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh
SCENE_DIR="$eval_dir/scenes/"

echo "Running MESS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -f SCENE_DIR

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Go to the mess_eval4/, which is where we will be running things
cd $eval_dir

# Activate conda environment
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate af_mess4

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename $scene_file)

# For eval 4, MESS only gave one submission -- commenting out multi
# submission bits from eval 3.75...

# Read in which submission to run from MCS config file
#SUBMISSION_ID=$(awk -F '=' '/submission_id/ {print $2}' $mcs_configfile | xargs)

# echo Running script_mess.py submission $SUBMISSION_ID

# run with SUBMISSION_ID set to '1' or '2' for both MESS submissions
#python3 script_mess.py scenes/$scene_file_basename $SUBMISSION_ID

python script_mess_eval4_ms.py scenes/$scene_file_basename

unset MCS_CONFIG_FILE_PATH

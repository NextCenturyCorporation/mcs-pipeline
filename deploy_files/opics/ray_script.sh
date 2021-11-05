#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh
SCENE_DIR="$eval_dir/eval_scene/"

echo "Running OPICS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:
echo 
# eval3: cd $eval_dir && source activate mcs_opics && python3 eval.py  --scenes $SCENE_DIR
# eval4:
sed -r -i 's/    python/    timeout -s 9 5m python/g' $eval_dir/opics.sh
# This allows us to change the timeout if we already set it
sed -r -i 's/timeout -s 9 [0-9]+. python/timeout -s 9 65m python/g' $eval_dir/opics.sh
cd $eval_dir && cp $mcs_configfile ./mcs_config.ini && bash -i opics.sh $SCENE_DIR

unset MCS_CONFIG_FILE_PATH

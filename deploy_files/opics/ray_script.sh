#!/bin/bash
set -m

main_optics
cd scripts/ || exit
OPICS_EVAL_DIR=$(pwd)

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154
SCENE_DIR="$eval_dir/eval_scene/"

# shellcheck disable=SC2154
echo "Running OPICS with config $mcs_configfile and scene $scene_file using eval dir $OPICS_EVAL_DIR"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out directories
echo Clearing History at "$OPICS_EVAL_DIR"/SCENE_HISTORY/
rm -f "$OPICS_EVAL_DIR"/SCENE_HISTORY/*
echo Clearing "$SCENE_DIR"
rm -rf "${SCENE_DIR:?}"/*

# Move files to appropriate locations
echo Making SCENE_DIR="$SCENE_DIR"
mkdir -p "$SCENE_DIR"
echo Moving scene_file="$scene_file" to "$SCENE_DIR"
cp "$scene_file" "$SCENE_DIR"/

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:
python opics_eval6_run_scene.py --scene "$SCENE_DIR"/"$scene_file"

unset MCS_CONFIG_FILE_PATH

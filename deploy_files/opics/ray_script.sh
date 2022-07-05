#!/bin/bash
set -m

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154
SCENE_DIR="$eval_dir/eval_scene/"

# shellcheck disable=SC2154
echo "Running OPICS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out directories
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

# Run the Performer code
echo Starting Evaluation:
opics_eval5
#run this because opics_eval5 sets xserver conf file
sudo nvidia-xconfig --no-use-display-device --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
cd "$eval_dir" && cp "$mcs_configfile" ../cfg/mcs_config.ini && bash -i ./opics.sh "$SCENE_DIR"

unset MCS_CONFIG_FILE_PATH

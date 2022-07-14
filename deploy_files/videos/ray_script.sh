#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

SCENE_DIR="$eval_dir/scenes/validation/"
TMP_CFG_FILE="$eval_dir/msc_cfg.ini.tmp"

echo "STARTING VIDEO GEN PIPELINE: CONFIG $mcs_configfile SCENE $scene_file"

# Set a bad config and kill the existing X Server before starting it again.
# Seems to be needed on non-Deep Learning AMIs. See README.
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:31:0
# Sleep here to ensure config file is written and X Server starts on boot
sleep 5
if pgrep -x Xorg > /dev/null
then
  echo "Killing existing X Server that started on boot"
  sudo kill $(pgrep -x Xorg)
  # Sleep here to ensure X Server is killed
  sleep 5
else
  echo "X Server wasn't started on boot"
fi

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $eval_dir/mcs_config.ini
rm $eval_dir/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $eval_dir/mcs_config.ini

# Run the Performer code
cd $eval_dir
SCENE_NAME=$(sed -nE 's/.*"name": "(\w+)".*/\1/pi' $scene_file)
echo "GENERATING RGB VIDEO: $scene_file ($SCENE_NAME)"
echo
source /home/ubuntu/venv/bin/activate

UNITY_APP=/home/ubuntu/unity_app/MCS-AI2-THOR-Unity-App-v0.5.6.x86_64

# Read variables from MCS config file
S3_BUCKET=$(awk -F '=' '/s3_bucket/ {print $2}' $mcs_configfile | xargs)
S3_FOLDER=$(awk -F '=' '/s3_folder/ {print $2}' $mcs_configfile | xargs)
EVAL_NAME=$(awk -F '=' '/evaluation_name/ {print $2}' $mcs_configfile | xargs)
TEAM_NAME=$(awk -F '=' '/team/ {print $2}' $mcs_configfile | xargs)

# Set the output prefix by checking if EVAL_NAME or TEAM_NAME are blank
[[ -z $EVAL_NAME || -z $TEAM_NAME ]] && OUTPUT_PREFIX=${EVAL_NAME}${TEAM_NAME} || OUTPUT_PREFIX=${EVAL_NAME}_${TEAM_NAME}

# Run the scene and create an mp4 video
if [ -z $OUTPUT_PREFIX ]
then
  python3 MCS/machine_common_sense/scripts/run_last_action.py --mcs_unity_build_file $UNITY_APP --config_file $mcs_configfile --save-videos $scene_file
else
  python3 MCS/machine_common_sense/scripts/run_last_action.py --mcs_unity_build_file $UNITY_APP --config_file $mcs_configfile --prefix $OUTPUT_PREFIX --save-videos $scene_file
fi

# Upload the mp4 video to S3 with credentials from the worker's AWS IAM role
OUTPUT_FOLDER=/home/ubuntu/output/
mkdir -p $OUTPUT_FOLDER
cp ${OUTPUT_PREFIX}*.mp4 $OUTPUT_FOLDER
aws s3 sync $OUTPUT_FOLDER s3://${S3_BUCKET}/${S3_FOLDER}/ --acl public-read

# Cleanup the worker for future use
rm ${OUTPUT_FOLDER}${OUTPUT_PREFIX}*.mp4

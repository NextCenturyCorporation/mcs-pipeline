#!/bin/bash
set -m

# This is what the "main_optics" command does (from the instructions TA1 gave us).
echo "OPICS Pipeline: Running TA1 environment setup..."
cd /home/ubuntu/ || exit
# Ensure that the virtual display (monitor resolution) is much greater than 600x400
sudo nvidia-xconfig --use-display-device=Device0 --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
export OUR_XPID=
export DISPLAY=:1
export OPTICS_HOME=~/main_optics
export PYTHONPATH=$OPTICS_HOME:$OPTICS_HOME/opics_common
export OPTICS_DATASTORE=ec2b
cd $OPTICS_HOME || exit
cd scripts/ || exit

# Start the X Server
# (Note that OPICS sets the DISPLAY to :1 -- Do NOT call start_x_server.sh)
sudo /usr/bin/Xorg :1 1>startx-out.txt 2>startx-err.txt &

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "OPICS Pipeline: Running OPICS with MCS config file $mcs_configfile and eval dir $eval_dir and scene file $scene_file"

echo "OPICS Pipeline: Removing previous scene history files in $eval_dir/SCENE_HISTORY/"
rm -f "$eval_dir"/SCENE_HISTORY/*
mkdir -p "$eval_dir"/SCENE_HISTORY/

# shellcheck disable=SC2207
CONTAINER_DIRS=($(ls /home/ubuntu/test__* -d))
for CONTAINER_DIR in "${CONTAINER_DIRS[@]}"; do
    echo "OPICS Pipeline: Removing previous scene history files in $CONTAINER_DIR/scripts/SCENE_HISTORY/"
    rm -f "$CONTAINER_DIR"/scripts/SCENE_HISTORY/*
done

export MCS_CONFIG_FILE_PATH=$mcs_configfile
python opics_eval7_run_scene.py --scene "$scene_file"
unset MCS_CONFIG_FILE_PATH

DEBUG=true

# Make sure to check for new container directories!
CONTAINER_DIRS=($(ls /home/ubuntu/test__* -d))
for CONTAINER_DIR in "${CONTAINER_DIRS[@]}"; do
    if [ $DEBUG ]; then echo "OPICS Pipeline: Found container directory: $CONTAINER_DIR"; fi
    HISTORY_DIR="$CONTAINER_DIR/scripts/SCENE_HISTORY/"
    if [ $DEBUG ]; then echo "OPICS Pipeline: Found scene history directory: $HISTORY_DIR"; fi
    # shellcheck disable=SC2207
    HISTORY_FILES=($(ls "$HISTORY_DIR"))
    for HISTORY_FILE in "${HISTORY_FILES[@]}"; do
        if [ $DEBUG ]; then echo "OPICS Pipeline: Found scene history file: $HISTORY_FILE"; fi
        # Remove the timestamp and the extension.
        SCENE_NAME=${HISTORY_FILE:0:-21}
        if [ $DEBUG ]; then echo "OPICS Pipeline: Scene name: $SCENE_NAME"; fi
        SCENE_DIR="$CONTAINER_DIR/scripts/$SCENE_NAME/"
        if [ -d "$SCENE_DIR" ]; then
            # Copy the MCS output files into the eval_dir so the ray pipeline can find them.
            echo "OPICS Pipeline: Scene directory was found! $SCENE_DIR"
            cp "$HISTORY_DIR/$HISTORY_FILE" "$eval_dir/SCENE_HISTORY/"
            cp -r "$SCENE_DIR" "$eval_dir/"
        else
            # Not necessarily an error; may be found in a different container directory.
            if [ $DEBUG ]; then echo "OPICS Pipeline: Scene directory not found: $SCENE_DIR"; fi
        fi
    done
done

echo "OPICS Pipeline: Running apt-get update and install..."
# Use "until" to (hopefully) avoid "dpkg frontend lock" errors which cause "install" to fail.
until sudo apt-get update; do :; done
until sudo apt-get install awscli -y; do :; done
echo "OPICS Pipeline: Installed the AWS CLI"

SCENE_NAME=$(sed -nE 's/.*"name": "(\w+)".*/\1/pi' "$scene_file")
DISAMBIGUATED_SCENE_NAME=$(basename "$scene_file" .json)

# Read these variables from the MCS config file.
S3_BUCKET=$(awk -F '=' '/s3_bucket/ {print $2}' "$mcs_configfile" | xargs)
S3_FOLDER=$(awk -F '=' '/s3_folder/ {print $2}' "$mcs_configfile" | xargs)
TEAM_NAME=$(awk -F '=' '/team/ {print $2}' "$mcs_configfile" | xargs)

TA1_LOG=${eval_dir}/logs/${DISAMBIGUATED_SCENE_NAME}_stdout.log
RENAMED_LOG=${eval_dir}/logs/${TEAM_NAME}_${SCENE_NAME}_stdout.log
mv "${TA1_LOG}" "${RENAMED_LOG}"

# Upload the mp4 video to S3 with credentials from the worker's AWS IAM role.
aws s3 cp "${RENAMED_LOG}" s3://"${S3_BUCKET}"/"${S3_FOLDER}"/ --acl public-read
echo "OPICS Pipeline: Uploaded ${TEAM_NAME}_${SCENE_NAME}_stdout.log"

#!/bin/bash

# Check passed mcs_config and scene file
# LOCAL_DIR=$(dirname $0)
# CHECK_PASSED_VAR_LOC="${LOCAL_DIR%/*}/check_passed_variables.sh"
# source $CHECK_PASSED_VAR_LOC
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154
# SCENE_DIR="$eval_dir/scenes/"

sudo apt install -y jq
scene_name=$(cat $scene_file | jq --raw-output '.name')
task_dir=""
if [[ $scene_name == sierra_* ]]
then
  task_dir="agent_id";
fi
if [[ $scene_name == tango_* ]]
then
  task_dir="moving_target";
fi
if [[ $scene_name == uniform_* ]]
then
  task_dir="lava";
fi
if [[ $scene_name == victor_* ]]
then
  task_dir="lava";
fi
if [[ $scene_name == whiskey_* ]]
then
  task_dir="ramp";
fi
if [[ $scene_name == xray_* ]]
then
  task_dir="solidity";
fi
if [[ $scene_name == yankee_* ]]
then
  task_dir="spatial_elimination";
fi
if [[ $scene_name == zulu_* ]]
then
  task_dir="support_relation";
fi
if [[ $scene_name == omega_* ]]
then
  task_dir="tool_scene";
fi
if [[ $task_dir == "" ]]
then
  echo "Cannot run NYU red team (formerly baseline) on scene $scene_name because task is unsupported"
  exit
fi
eval_dir=${eval_dir}/${task_dir}

# shellcheck disable=SC2154
echo "Running NYU red team (formerly baseline) with MCS config $mcs_configfile and scene $scene_file with name $scene_name using eval dir $eval_dir"

# Set a bad config and kill the existing X Server before starting it again.
# Seems to be needed on non-Deep Learning AMIs. See README.
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:31:0
# Sleep here to ensure config file is written and X Server starts on boot
sleep 5
if pgrep -x Xorg > /dev/null
then
  echo "Killing existing X Server that started on boot"
  sudo kill "$(pgrep -x Xorg)"
  # Sleep here to ensure X Server is killed
  sleep 5
else
  echo "X Server wasn't started on boot"
fi

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*
#echo Clearing "$SCENE_DIR"
#rm -rf "${SCENE_DIR:?}"/*
#
## Move files to appropriate locations
#echo Making SCENE_DIR="$SCENE_DIR"
#mkdir -p "$SCENE_DIR"
#echo Moving scene_file="$scene_file" to "$SCENE_DIR"
#cp "$scene_file" "$SCENE_DIR"/
##scene_name=${scene_file##*/}

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
cd "$eval_dir" || exit
echo Starting Evaluation:
echo "$eval_dir"

../venv/bin/python main.py --scene_path $scene_file

unset MCS_CONFIG_FILE_PATH

#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

scene_name=$(cat $scene_file | jq --raw-output '.name')

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
rm -f "$eval_dir"/SCENE_HISTORY/*

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
cd "$eval_dir" || exit

../venv/bin/python main.py --scene_path $scene_file

unset MCS_CONFIG_FILE_PATH

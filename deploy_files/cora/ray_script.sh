#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "Running CORA with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X

# This works for p2 but not for gd4n (device naem can't be none on p3/g4dn)
# source /home/ubuntu/start_x_server.sh
if pgrep -x Xorg > /dev/null
then
  echo 'X Server is running'
else
  echo "Starting X Server"
  sudo nvidia-xconfig --use-display-device=Device0 --virtual=600x400 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
  sudo /usr/bin/Xorg :0 1>startx-out.txt 2>startx-err.txt &
  echo "Sleeping for 20 seconds to wait for X server"
  sleep 20
  echo "Sleep finished"

  if pgrep -x Xorg > /dev/null
  then
    echo 'Successfully started X Server'
  else
    echo 'Error:  Unable to start X Server!!'
    exit 1
  fi
fi



export DISPLAY=:0

# Clear out directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:

# conda init bash 
# exec bash -l

source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate jax

# Adjust for where they hardcoded the scene file to be read from, might be different next collab/evaluation run
mkdir /home/ubuntu/scenes/caci
cd /home/ubuntu/scenes/caci/ || exit
rm ./*
cp "$scene_file" .
# End Adjust

cd "$eval_dir" || exit
# for p2
# source /home/ubuntu/CoraAgent/venv/bin/activate && DISPLAY=:0 julia --project test/runtests.jl  /home/ubuntu/validation_6

# for g4dn/p3?
# source /home/ubuntu/CoraAgent/venv/bin/activate <- julia will do this
# sudo nohup Xorg :0 -config /etc/X11/xorg.conf & DISPLAY=:0 julia --project test/runtests.jl /home/ubuntu/scenes/tmp/
julia --project test/runtests.jl /home/ubuntu/scenes/caci/

# source /home/ubuntu/CoraAgent/venv/bin/activate && sudo nohup Xorg :4 -config /etc/X11/xorg.conf & DISPLAY=:4 julia --project test/runtests.jl  /home/ubuntu/validation_6

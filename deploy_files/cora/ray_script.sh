#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "Running CORA with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Clear out directories
echo Clearing History at "$eval_dir"/SCENE_HISTORY/
rm -f "$eval_dir"/SCENE_HISTORY/*
export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation for CORA:

# Adjust for where they hardcoded the scene file to be read from, might be different next collab/evaluation run
echo "Copy Scene Files:"
mkdir -p /home/ubuntu/scenes/evaluation_6
cd /home/ubuntu/scenes/evaluation_6 || exit
rm ./*
cp "$scene_file" .
echo $(basename "$scene_file")
cd "$eval_dir" || exit

# Source the conda environment 
echo "Starting jax env"
cd /home/ubuntu/CoraAgent || exit
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate jax

# Start X
#Not used
#source /home/ubuntu/start_x_server.sh
if pgrep -x Xorg > /dev/null
then
  echo 'X Server is running'
else
  echo "Starting X Server"
  # FOR CORA - they modify /etc/X11/xorg.conf, so dont run xconfig
  sudo /usr/bin/Xorg :0 -config /etc/X11/xorg.conf 1>startx-out.txt 2>startx-err.txt &
  echo "Sleeping for 20 seconds to wait for X server"
  sleep 20
  echo "Sleep finished"
fi

if pgrep -x Xorg > /dev/null
then
  echo 'Successfully started X Server'
else
  echo "Sleeping for another 20 seconds to wait for X server"
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

if pgrep -f "python /home/ubuntu/jax3dp3/scripts/run_physics_server.py" > /dev/null
then
  echo 'Physics server is running'
else
  echo "Starting run_physics_server.py"
  # Need to redirect logs of background tasks or the script doesn't
  python /home/ubuntu/jax3dp3/scripts/run_physics_server.py 1>physserver-out.txt 2>physserver-err.txt &
  echo "Sleeping for 20 seconds to wait for physics server"
  sleep 20
fi

if pgrep -f "python /home/ubuntu/jax3dp3/experiments/multiprocess/server.py" > /dev/null
then
  echo 'Vision server is running'
else
  echo "Starting server.py"
  cd /home/ubuntu/jax3dp3/experiments/multiprocess || exit
  # Need to redirect logs of background tasks or the script doesn't
  python server.py 1 >pyserver-out.txt 2>pyserver-err.txt &
  echo "Sleeping for 20 seconds to wait for vision server"
  sleep 20
fi

# CORA has a harded coded Display value in one module, must be 0 (Eval 6)
export DISPLAY=:0

## Running the Scene. You can run this in a separate shell/tmux sessions or in the same shell too
cd /home/ubuntu/CoraAgent || exit
DISPLAY=:0 julia --project test/runtests.jl /home/ubuntu/scenes/evaluation_6

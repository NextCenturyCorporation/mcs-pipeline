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
mkdir -p /home/ubuntu/scenes/evaluation_7
cd /home/ubuntu/scenes/evaluation_7 || exit
rm ./*
cp "$scene_file" .
echo $(basename "$scene_file")
cd "$eval_dir" || exit

# Source the conda environment 
echo "conda activate old_bayes3d"
cd /home/ubuntu/Cora2/CoraAgent || exit
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate old_bayes3d

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

#Physics Server
# cd /home/ubuntu/bayes3d || exit
# if pgrep -f "python /home/ubuntu/bayes3d/run_mcs_physics.py" > /dev/null
# then
#   echo 'Physics server is running'
# else
#   echo "Starting run_physics_server.py"
#   # Need to redirect logs of background tasks or the script doesn't
#   python python /home/ubuntu/bayes3d/run_mcs_physics.py 1>physserver-out.txt 2>physserver-err.txt &
#   echo "Sleeping for 20 seconds to wait for physics server"
#   sleep 20
# fi

if pgrep -f "python /home/ubuntu/old_bayes3d/icra-bayes3d/experiments/multiprocess/server.py" > /dev/null
then
  echo 'server.py is running'
else
  echo "Starting server.py"
  cd /home/ubuntu/old_bayes3d/icra-bayes3d/experiments/multiprocess || exit
  # Need to redirect logs of background tasks or the script doesn't
  python /home/ubuntu/old_bayes3d/icra-bayes3d/experiments/multiprocess/server.py 1 >pyserver-out.txt 2>pyserver-err.txt &
  echo "Sleeping for 30 seconds to wait for server"
  sleep 20
fi

# CORA has a harded coded Display value in one module, must be 0 (Eval 6)
export DISPLAY=:0

## Running the Scene. You can run this in a separate shell/tmux sessions or in the same shell too
cd /home/ubuntu/Cora2/CoraAgent || exit
# DISPLAY=:0 julia --project test/runtests.jl /home/ubuntu/scenes/evaluation_7

##########################################################


# check if monitor process is specified as 'true' in config file
HAS_MON_PROC=$(awk -F '=' '/has_monitor_process/ {print tolower($2)}' "$mcs_configfile" | xargs)
echo has_monitor_process is "$HAS_MON_PROC"

if [ "$HAS_MON_PROC" = true ];
then
    # kick off monitor process
    # if using this monitor_process bit for other performers, make sure the two
    # arguments are pointing to the correct places + update lines 72, 74 and 81 if
    # changing anything about the monitor_process.py command
    # see monitor_process.py for more on how to use + update things properly.
    python /home/ubuntu/monitor_process.py "$scene_file_basename" "$eval_dir" &
    sleep 5
    mon_proc_id=$(pgrep -f "python /home/ubuntu/monitor_process.py ${scene_file_basename} ${eval_dir}")
    echo Monitor process ID for "$scene_file" is: "$mon_proc_id"

    # TA1 run command
    DISPLAY=:0 julia --project test/runtests.jl /home/ubuntu/scenes/evaluation_7
  
    # end monitor process
    echo "Monitor process ID: ${mon_proc_id}, checking if it has ended for scene: ${scene_file_basename}"
    if pgrep -f "python /home/ubuntu/monitor_process.py ${scene_file_basename} ${eval_dir}" > /dev/null
    then
        echo "Scene finished, attempt to terminate monitor_process.py with id ${mon_proc_id}"
        kill -15 "$mon_proc_id"
        echo "Sleeping for 20 seconds to wait for monitor process to end"
        sleep 20
    fi
else
    # TA1 run command
    DISPLAY=:0 julia --project test/runtests.jl /home/ubuntu/scenes/evaluation_7
fi

unset MCS_CONFIG_FILE_PATH

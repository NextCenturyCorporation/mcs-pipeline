#!/bin/bash

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154
SCENE_DIR="$eval_dir/scenes/"

# shellcheck disable=SC2154
echo "Running MESS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
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

# Go to the mess-eval6/, which is where we will be running things
cd "$eval_dir" || exit

# Activate mamba/conda environment
source /home/ubuntu/mambaforge/etc/profile.d/conda.sh
conda activate mess6

# if DISPLAY environment variable is set in their environment,
# unset it - they are setup a little differently and use vncserver
# instead
unset DISPLAY

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename "$scene_file")

# For eval 4+, MESS only gave one submission -- commenting out multi
# submission bits from eval 3.75...

# Read in which submission to run from MCS config file
#SUBMISSION_ID=$(awk -F '=' '/submission_id/ {print $2}' $mcs_configfile | xargs)

# echo Running script_mess.py submission $SUBMISSION_ID

# run with SUBMISSION_ID set to '1' or '2' for both MESS submissions
#python3 script_mess.py scenes/$scene_file_basename $SUBMISSION_ID

# For tasks that don't finish/end_scene is never explicitly called, you may need
# to do something like this:
# timeout 7200 python src/script_mess_clean.py scenes/"$scene_file_basename"

# kick off monitor process (if specified in config file)
# if using this monitor_process bit for other performers, make sure the two
# arguments are pointing to the correct places + update lines 66, 68 and 76 if
# changing anything about the monitor_process.py command
# see monitor_process.py for more on how to use + update things properly.
HAS_MON_PROC=$(awk -F '=' '/has_monitor_process/ {print tolower($2)}' "$mcs_configfile" | xargs)
echo has_monitor_process is "$HAS_MON_PROC"

if [ "$HAS_MON_PROC" = true ];
then
    python /home/ubuntu/monitor_process.py "$scene_file_basename" "$eval_dir" &
    mon_proc_id=$(pgrep -f "python /home/ubuntu/monitor_process.py ${scene_file_basename} ${eval_dir}")
    echo Monitor process ID for "$scene_file" is: "$mon_proc_id"

    # TA1 run command
    python src/script_mess_clean.py scenes/"$scene_file_basename"

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
    python src/script_mess_clean.py scenes/"$scene_file_basename"
fi

unset MCS_CONFIG_FILE_PATH

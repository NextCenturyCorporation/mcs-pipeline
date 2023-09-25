#!/bin/bash

# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154

echo "monitor_process.sh: starting for ${scene_file}"
scene_file_basename=$(basename "$scene_file")

# TA1 run command
ta1_run_cmd="python src/script_mess_clean.py scenes/${scene_file_basename}"
# Skip termination steps on first pass that history file is found, in case file is currently being uploaded
first_run=true

while true; do
    # check if TA1 process is running by looking for their run command
    if pgrep -f "${ta1_run_cmd}"> /dev/null
    then
        # check for scene history file, if one exists then end script_mess_clean process
        #
        # need to get non-obfuscated filename from scene file, then use that to look for an existing
        # history file
        python_process=$(pgrep -f "${ta1_run_cmd}")
        echo "monitor_process.sh: python process is ${python_process}"
        echo monitor_process.sh: Checking for history file for: "$filename"
        filename=$(grep -o '"name": "[^"]*' scenes/"$scene_file_basename" | grep -o '[^"]*$')
        # shellcheck disable=SC2154
        if compgen -G "${eval_dir}/SCENE_HISTORY/${filename}*.json" > /dev/null
        then
            if [ "$first_run" = true ];
            then
                echo "monitor_process.sh: History file exists for ${filename}, skipping process termination on first pass in case file is currently being uploaded."
                first_run=false
            else
                echo "monitor_process.sh: History file for ${filename} exists, terminate process."
                echo "monitor_process.sh: Terminate child unity process first"
                child_processes=$(pgrep -P "$python_process")
                for cpid in $child_processes;
                do
                    if ps -p "$cpid" > /dev/null
                    then
                        echo "monitor_process.sh: Attempt to terminate process ${cpid}"
                        kill -15 "$cpid"
                    fi
                done

                echo "monitor_process.sh: Terminate main process now"
                pkill -f "${ta1_run_cmd}"
                sleep 20
                echo "monitor_process.sh: exiting for ${scene_file}"
                exit 1
            fi
        fi
    fi
    echo "monitor_process.sh: Sleeping for half an hour to wait for output for ${scene_file}"
    sleep 1800
done

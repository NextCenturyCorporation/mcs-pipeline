#!/bin/bash

# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh
# shellcheck disable=SC2154

while true; do
    # check if TA1 process is running by looking for their run command
    if pgrep -f "python src/script_mess_clean.py scenes/{$scene_file_basename}" > /dev/null
    then
        # check for scene history file or timeout in logs, if one exists then end script_mess_clean process
        # need to get non-obfuscated filename from scene file, then use that to look for an existing
        # history file
        filename=$(grep -o '"name": "[^"]*' scenes/"$scene_file_basename" | grep -o '[^"]*$')
        if compgen -G "{$eval_dir}/SCENE_HISTORY/{$filename}*.json" > /dev/null
        then
            echo "History file exists, kill process."
            pkill -f "python src/script_mess_clean.py scenes/{$scene_file_basename}"
            sleep 20 # TODO: MCS-1771: is this sufficient
            exit 1
        fi
    fi
    echo "Sleeping for 2 1/2 hours to wait for output"
    sleep 9000
done

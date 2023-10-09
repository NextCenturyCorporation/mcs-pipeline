import os
import time
import sys
from subprocess import Popen, PIPE
import json
import glob
import psutil
import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def main(scene_file_basename, eval_dir, full_scene_file_path, full_cmd):
    """
    This script is only needed for situations where the performer code gets
    stuck/no steps are taken. If that happens, you should see something like
    this in your logs:
    "Attempting to end scene due to inactivity (user not taking any steps) for 1:00:00 (hh:mm:ss)"

    In this case, a history file + video files should be created, but the parent process
    might not exit, leaving things in a hung state (hence the need for this script).

    If using this script for other performers, double check that
    the following variables are updated and correct:
    scene_file_basename, eval_dir, full_scene_file_path, full_cmd

    Then, copy this script into deploy_files/{team} and update your
    team config in mako/variables/{team}.yaml with the
    additional_file_mounts + additional_setup_commands like in mess.yaml, and that
    has_monitor_process is set to 'true'.
    Also be sure to update ray_script.sh with the relevant parts (see
    deploy_files/mess/ray_script.sh for an example).
    """
    logging.info("monitor_process.py: starting with the following args: ")
    logging.info(
        f"monitor_process.py: scene_file_basename: {scene_file_basename}"
    )
    logging.info(f"monitor_process.py: eval_dir: {eval_dir}")
    logging.info(
        f"monitor_process.py: full_scene_file_path: {full_scene_file_path}"
    )
    logging.info(f"monitor_process.py: full_cmd: {full_cmd}")
    time.sleep(10)
    first_run = True
    sleep_time = 1800

    while True:
        logging.info(
            f"monitor_process.py: check for running process: {full_cmd}"
        )
        child = Popen(["pgrep", "-f", "^" + full_cmd], stdout=PIPE, shell=False)
        result = child.communicate()[0]
        result_array = [int(pid) for pid in result.split()]

        if len(result_array) > 0:

            logging.info(
                f"monitor_process.py: process found with process ID: {result_array[0]}"
            )

            with open(full_scene_file_path, "r") as f:
                data = json.load(f)
                proper_filename = data["name"]

            history_files = f"{eval_dir}/SCENE_HISTORY/{proper_filename}*.json"
            scene_hist_matches = glob.glob(history_files)

            # check if history file exists
            if len(scene_hist_matches) > 0:
                found_scene_hist = max(scene_hist_matches, key=os.path.getctime)

                if first_run:
                    # ignore first instance of found file, in case it is being uploaded as normal + there are no timeouts
                    logging.info(
                        f"monitor_process.sh: history file exists for {proper_filename}, "
                        f"skipping process termination on first pass in case file is currently being uploaded."
                    )
                    first_run = False
                    # shorten timeout in this case, since file upload should happen relatively quickly if scene file run goes smoothly.
                    sleep_time = 600
                else:
                    logging.info(
                        f"monitor_process.sh: found history file for {proper_filename} here: {found_scene_hist}, scene file runner process may be hung, attempting to end process."
                    )

                    for p in psutil.process_iter(["pid"]):
                        if p.info["pid"] == result_array[0]:
                            children = p.children(recursive=True)
                            for c_process in children:
                                logging.info(
                                    f"monitor_process.py: child process of {result_array[0]}: {c_process}"
                                )
                                if "MCS-AI2-THOR" in c_process.name():
                                    logging.info(
                                        f"monitor_process.py: found child Unity process: "
                                        f"{c_process}, will attempt to end."
                                    )
                                    c_process.terminate()

                            logging.info(
                                f"monitor_process.py: now attempting to end main process {p}"
                            )
                            p.terminate()

                    time.sleep(10)

                    sys.exit()

        # if no process or file isn't found, sleep for a while
        logging.info(
            f"monitor_process.py: sleep for {str(int(sleep_time / 60))} mins to wait for output for {scene_file_basename}"
        )
        time.sleep(sleep_time)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        logging.info(
            "monitor_process.py: not enough arguments passed in, exiting. "
        )
        sys.exit()

    main(
        scene_file_basename=sys.argv[1],
        eval_dir=sys.argv[2],
        full_scene_file_path=sys.argv[3],
        full_cmd=sys.argv[4],
    )

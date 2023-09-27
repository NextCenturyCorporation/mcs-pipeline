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


def main(scene_file_basename, eval_dir):
    logging.info("monitor_process.py: starting with the following args: ")
    time.sleep(10)

    logging.info(
        f"monitor_process.py: scene_file_basename: {scene_file_basename}"
    )
    logging.info(f"monitor_process.py: eval_dir: {eval_dir}")
    # TA1 run command and full scene file path
    full_cmd = "python src/script_mess_clean.py scenes/" + scene_file_basename
    full_scene_file_path = eval_dir + "/scenes/" + scene_file_basename
    first_run = True
    sleep_time = 1800

    while True:
        logging.info(
            f"monitor_process.py: check for running process: {full_cmd}"
        )
        child = Popen(["pgrep", "-f", full_cmd], stdout=PIPE, shell=False)
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
                                if c_process.name == "MCS-AI2-THOR":
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
    if len(sys.argv) != 3:
        logging.info(
            "monitor_process.py: not enough arguments passed in, exiting. "
        )
        sys.exit()

    main(scene_file_basename=sys.argv[1], eval_dir=sys.argv[2])

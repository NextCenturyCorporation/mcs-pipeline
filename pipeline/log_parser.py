import logging
import os
import re
import pathlib
import shutil


def split_log(file='out.txt'):
    sort_dir = 'test'
    sort = pathlib.Path(sort_dir)
    shutil.rmtree(sort, ignore_errors=True)
    sort.mkdir(parents=True)

    with open(file, "r") as f:
        for line in f:
            # print(line)
            # ts = re.search("^(\\d{2}:\\d{2}:\\d{2})", line)

            pid_group = re.search("\\(pid=(\\d+)", line)
            pid = pid_group.groups()[0] if pid_group is not None else None

            if pid is not None:
                ip_group = re.search("ip=(\\d+\\.\\d+\\.\\d+\\.\\d+)", line)
                ip = ip_group.groups()[0] if ip_group is not None else 'head'
                out_file = sort / f"{ip}.txt"
                with open(out_file, 'a') as out:
                    out.write(pid_group.string)
                    out.flush()
                    out.close()

    runs = []
    for (base, folders, files) in os.walk(sort):
        for file in files:
            my_runs = parse_single_server_file(sort/file)
            runs = runs + my_runs

    total = ExecutionStats(0)
    for run in runs:
        for key in run.times:
            val = run.times[key]
            total.add_time(val, key)
            total.last_time = 0
    print("-------TOTAL-------")
    total.print()

    ave = ExecutionStats(0)
    for key in total.times:
        val = total.times[key] / len(runs)
        val = int(val)
        ave.add_time(val, key)
    print("-------AVERAGE-------")
    ave.print()

    print(f"runs: {len(runs)}")


class ExecutionStats():
    start = -1
    end = -1
    last_time = -1

    def __init__(self, start_time) -> None:
        self.start = start_time
        self.last_time = self.start
        self.times = {}

    def add_time(self, ts: int, name: str):
        last = ts
        ts = ts - self.last_time
        val = self.times.get(name, 0)
        val += ts
        self.times[name] = val
        self.last_time = last

    def end_exe(self, ts: int):
        self.end = ts

    def pretty_print(self, ts: int):
        result = ""
        while True:
            rem = str(ts % 60)
            rem = f"0{rem}" if len(rem) == 1 else rem
            ts = int(ts / 60)
            delim = ":" if ts > 0 else ""
            result = f"{delim}{rem}{result}"
            if ts < 1:
                return result

    def print(self):
        for key in self.times:
            val = self.times[key]
            print(f"{key}:  {self.pretty_print(val)}")


def parse_single_server_file(file: pathlib.Path):
    mcs_found = "Found path: /home/ubuntu/"
    mcs_started = "Initialize return: {'cameraNearPlane'"
    elements = [
        ("start", "copying files to subsystem-specific scene directories..."),
        ("setup", "running pvoe scenes"),
        ("pre-work", mcs_found),
        ("init", mcs_started),
        ("run-pvoe", "pvoe scenes complete"),
        ("setup", "running avoe scenes"),
        ("pre-work", mcs_found),
        ("init", mcs_started),
        ("run-avoe", "avoe scenes complete"),
        ("setup", "running interactive scenes"),
        ("pre-work", mcs_found),
        ("init", mcs_started),
        ("run-interactive", "interactive scenes complete")]

    # start_eval = "In run scene.  Running"
    # end_eval = "History file timestamp:"

    start = None
    exe_stat = None
    element_index = 0

    runs = []

    with open(file, "r") as f:
        for line in f:
            if elements[0][1] in line:
                start = get_timestamp(line)
                start = process_time(start)
                exe_stat = ExecutionStats(start)
                element_index = 1
            elif exe_stat is not None and elements[element_index][1] in line:
                timestamp = get_timestamp(line)
                ts = process_time(timestamp)
                exe_stat.add_time(ts, elements[element_index][0])
                element_index += 1
                if element_index == len(elements):
                    element_index = 0
                    exe_stat.end_exe(ts)
                    exe_stat.print()
                    runs.append(exe_stat)

    return runs


def process_time(start_time: str):
    split = start_time.split(":")
    return int(split[0]) * 3600 + int(split[1]) * 60 + int(split[2])


def get_timestamp(line):
    ts = re.search("^(\\d{2}:\\d{2}:\\d{2})", line)
    return ts.groups()[0]


def main(args):
    """Generate and save one or more MCS JSON scenes using the given config
    for the Ideal Learning Environment (ILE)."""
    logger = logging.getLogger()
    logger.debug("starting")
    split_log('tmp2.txt')


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(
    #    description='Parse log files.'
    # )
    
    # args = parser.parse_args()
    main(None)
import argparse
import logging
import os
import re
import pathlib
import shutil
from typing import List

IP_REGEX = "ip=(\\d+\\.\\d+\\.\\d+\\.\\d+)"
PID_REGEX = "\\(pid=(\\d+)"
TIMESTAMP_REGEX = "^(\\d{2}:\\d{2}:\\d{2})"


class ExecutionStats():
    start = -1
    end = -1
    last_time = -1
    name = ""
    group = ""

    def __init__(self, start_time) -> None:
        self.start = start_time
        self.last_time = self.start
        self.times = {}

    def add_time(self, ts: int, name: str):
        last = ts
        ts -= self.last_time
        val = self.times.get(name, 0)
        val += ts
        self.times[name] = val
        self.last_time = last

    def set_time(self, ts: int, name: str):
        self.times[name] = ts

    def end_exe(self, ts: int):
        self.end = ts

    def get_pretty_print_time(self, ts: int):
        """take an integer value of seconds and convert to
        'days:hours:minutes:seconds' format.  hours/minutes/seconds will be 2
        digit with leading 0 when necessary. """
        seconds = ts % 60
        minutes = int(ts / 60) % 60
        hours = int(ts / 3600) % 60
        days = int(ts / (3600 * 60) % 24)
        return f"{days}:{hours:02d}:{minutes:02d}:{seconds:02d}"

    def pretty_print(self):
        print(f"Name:{self.name}\nGroup:{self.group}")
        for key in self.times:
            val = self.times[key]
            print(f"{key:<20}:  {self.get_pretty_print_time(val)}")


class LogMatcher():
    def __init__(self, name, regex) -> None:
        self.name = name
        self.regex = regex

    def is_matched(self, line):
        result = self.get_match_group(line)
        return result is not None

    def get_match_group(self, line):
        return re.search(self.regex, line)


class RayLogProcessor():

    @staticmethod
    def split_and_process_log(file: str, output_dir: pathlib.Path, matchers: List[LogMatcher]):
        RayLogProcessor._split_log(file, output_dir)
        return RayLogProcessor._process_files_in_directory(output_dir, matchers)

    @staticmethod
    def _split_log(file, output_dir: pathlib.Path):
        """Takes a long file from ray and splits into separate files for each
        server based on IP from log."""
        # TODO open files only once?  leave open and cache
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)

        with open(file, "r") as f:
            for line in f:
                # print(line)
                # ts = re.search("^(\\d{2}:\\d{2}:\\d{2})", line)

                pid_group = re.search(PID_REGEX, line)
                pid = pid_group.groups()[0] if pid_group is not None else None

                if pid is not None:
                    ip_group = re.search(IP_REGEX, line)
                    ip = (ip_group.groups()[0]
                          if ip_group is not None else 'head')
                    out_file = output_dir / f"{ip}.txt"
                    with open(out_file, 'a') as out:
                        out.write(pid_group.string)
                        out.flush()
                        out.close()

    @staticmethod
    def _parse_single_server_file(file: pathlib.Path, matchers: List[LogMatcher]):
        start = None
        exe_stat = None
        index = 0

        runs = []
        name_matcher = "Pushing .* to .*/.*_([A-Za-z]+_[0-9]{4}_[0-9]{2}.json)"

        with open(file, "r") as f:
            for line in f:

                if matchers[0].is_matched(line):
                    start = get_timestamp(line)
                    start = convert_timestamp_to_int(start)
                    exe_stat = ExecutionStats(start)
                    index = 1
                elif exe_stat is not None and matchers[index].is_matched(line):
                    timestamp = get_timestamp(line)
                    ts = convert_timestamp_to_int(timestamp)
                    exe_stat.add_time(ts, matchers[index].name)
                    index += 1
                    if index == len(matchers):
                        index = 0
                        exe_stat.end_exe(ts)
                        exe_stat.pretty_print()
                        runs.append(exe_stat)
                if exe_stat is not None:
                    result = re.search(name_matcher, line)
                    if result is not None:
                        exe_stat.name = result.groups()[0]
                        exe_stat.group = exe_stat.name.split('_')[0]
                        print(exe_stat.name)

        return runs

    @staticmethod
    def _process_files_in_directory(output_dir: pathlib.Path, matchers):
        """Takes a directory and a bunch of matchers and processes each file to
        get timing for each found execution."""
        runs = []
        for (base, folders, files) in os.walk(output_dir):
            for file in files:
                my_runs = RayLogProcessor._parse_single_server_file(
                    output_dir/file,
                    matchers)
                runs += my_runs
        return runs

    @staticmethod
    def debug_print_runs(runs, print_total=False):
        """Print results of runs for debugging"""
        total = ExecutionStats(0)
        for run in runs:
            for key in run.times:
                val = run.times[key]
                total.add_time(val, key)
                total.last_time = 0
        if print_total:
            print("  -total-")
            total.pretty_print()

        ave = ExecutionStats(0)
        for key in total.times:
            val = total.times[key] / len(runs)
            val = int(val)
            ave.set_time(val, key)
        print("  -average-")
        ave.pretty_print()

        print(f"runs: {len(runs)}")


def get_opics_matchers():
    return [
        LogMatcher(
            'start', "copying files to subsystem-specific scene directories..."),
        LogMatcher('split-overhead',
                   "(running pvoe scenes)|(running avoe scenes)|(running interactive scenes)"),
        LogMatcher('found-ai2thor', "Found path: /home/ubuntu/"),
        LogMatcher('setup', "Initialize return: {'cameraNearPlane'"),
        LogMatcher(
            'Run', "(pvoe scenes complete)|(avoe scenes complete)|(interactive scenes complete)"),
        LogMatcher(
            'Upload', "Pushing .*\\.log"),
    ]


def get_default_matchers():
    return [
        LogMatcher(
            'Start', "In run scene."),
        LogMatcher('Initialization', "Found path:"),
        LogMatcher('Finish scene', "History file timestamp")
    ]


def convert_timestamp_to_int(start_time: str):
    split = start_time.split(":")
    return int(split[0]) * 3600 + int(split[1]) * 60 + int(split[2])


def get_timestamp(line):
    ts = re.search(TIMESTAMP_REGEX, line)
    return ts.groups()[0]


def main(args):
    """Generate and save one or more MCS JSON scenes using the given config
    for the Ideal Learning Environment (ILE)."""
    logger = logging.getLogger()
    logger.debug("starting")
    log_file = args.log_file
    output_dir = pathlib.Path(args.output_dir)
    matchers = None
    if args.matchers == 'OPICS':
        matchers = get_opics_matchers()
    else:
        logger.error(
            f"Warning: Matchers not defined for {args.matchers}.  Using Defaults")
        matchers = get_default_matchers()
    runs = RayLogProcessor.split_and_process_log(
        log_file, output_dir, matchers)

    groups = {}
    for run in runs:
        groups[run.group] = []
    for run in runs:
        groups[run.group].append(run)

    for key in groups:
        val = groups[key]
        print(f"\n----**{key}**----")
        RayLogProcessor.debug_print_runs(val, False)

    RayLogProcessor.debug_print_runs(runs, True)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Parse log files.'
    )
    parser.add_argument('--output-dir', '-o', default='./split_logs/')
    parser.add_argument('log_file')
    parser.add_argument(
        '--matchers', '-m', choices=['OPICS', 'MESS', 'CORA', 'BASELINE'], default='OPICS')

    args = parser.parse_args()
    main(args)

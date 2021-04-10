#
# Run all the tasks (in directory taskfiles/) on all the machines that we have.
#
import ray

from pipeline import logger
from pipeline import util
from pipeline.baseline_singletask_ray import BaselineSingleTaskRay
from pipeline.xserver_check import XServerCheck
from pipeline.xserver_startup import XServerStartup

# TASK_FILE_PATH = "tasks_delta_echo_foxtrot.txt"
TASK_FILE_PATH = "tasks_single_task.txt"


@ray.remote
def run_task(task_file):
    print(f"Got to here {task_file}")
    # Run the task
    singleTask = BaselineSingleTaskRay(task_file, None)
    return_code = singleTask.process()

    if return_code > 0:
        print(f"Task for file {task_file} failed. Adding back to the queue")
        #  TODO:  Figure out how to report failure
        # task_files_full_path.append(task_file)


@ray.remote
class BaselineRunTasks:

    def __init__(self):
        self.task_files_list = []

        dateStr = util.get_date_in_file_format()
        self.log = logger.configure_base_logging(dateStr + ".log")
        self.log.info("Starting runtasks")

        self.get_tasks()
        self.run_tasks()

    def get_tasks(self):
        util.run_command_and_capture_output('ls', self.log)
        task_file = open(TASK_FILE_PATH, 'r')
        lines = task_file.readlines()
        for line in lines:
            if line is not None and len(line) > 0:
                self.task_files_list.append(line.strip())

        self.task_files_list.sort()
        self.log.info(f"Number of tasks: {len(self.task_files_list)}")
        self.log.info(f"Tasks {self.task_files_list}")

    def run_tasks(self):
        object_ids = [run_task.remote(task) for task in self.task_files_list]
        ip_addresses = ray.get(object_ids)
        self.log.info("Ending runtasks")

    def run_xstartup(self):
        ''' Start X Server on all the machines.  Note:  Not parallelized'''
        for machine in self.available_machines:
            bs = XServerStartup(machine, self.log)
            bs.process()

    def run_check_xorg(self):
        self.available_machines = util.get_aws_machines()
        self.log.info(f"Machines available {self.available_machines}")

        for machine in self.available_machines:
            bs = XServerCheck(machine, self.log)
            bs.process()


if __name__ == '__main__':
    ray.init()
    # ray.init(address='auto')
    try:
        baseline_run_tasks = BaselineRunTasks.remote()
    except Exception as e:
        print(f"exception {e}")

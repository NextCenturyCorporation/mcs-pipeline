#
# Run all the tasks (in directory taskfiles/) on all the machines that we have.
#
import threading

from pipeline import logger
from pipeline import util
from pipeline.cora_singletask import CoraSingleTask
from pipeline.mcs_test_runner import McsTestRunner
from pipeline.xserver_startup import XServerStartup

# Uncomment one of the following.  single is for testing;
# TASK_FILE_PATH = "scenes_single_scene.txt"
TASK_FILE_PATH = "../scenes_juliett.txt"

# Config file location
config_on_local = "mcs_config_cora_level2.ini"
remote_config_file_directory = "/home/ubuntu/workspace/GenPRAM.jl/GenAgent/omg/"


class CoraRunTasks:

    def __init__(self):
        self.available_machines = []
        self.task_files_full_path = []

        # Main Logger
        dateStr = util.get_date_in_file_format()
        self.log = logger.configure_base_logging(dateStr + ".log")
        self.log.info("Starting runtasks")

    def run_thread_on_ec2_machine(self, machine_dns):
        """ Function that runs on its own thread, with thread-local variable
        of the machine to use.  While there are more task files to run, get
        one and run it, exiting the thread when there are no more tasks."""
        dateStr = util.get_date_in_file_format()
        threadlog = logger.configure_logging(machine_dns, dateStr +
                                             "." + machine_dns)

        # Lock to be able to count tasks remaining and get one in a
        # thread-safe way. Otherwise, we could count tasks remaining and
        # before we pop it, some other thread might pop it
        lock = threading.RLock()
        while True:
            lock.acquire()
            if len(task_files_list) == 0:
                lock.release()
                return
            task_file = task_files_list.pop(0)
            lock.release()

            singleTask = CoraSingleTask(machine_dns, task_file, threadlog)
            return_code = singleTask.process()

            if return_code > 0:
                lock.acquire()
                self.log.warning(f"Task for file {task_file} failed.  " +
                                 "Adding back to the queue")
                task_files_list.append(task_file)
                lock.release()

    def get_tasks(self):
        global task_files_list

        task_files_list = []
        task_file = open(TASK_FILE_PATH, 'r')
        lines = task_file.readlines()
        for line in lines:
            if line is not None and len(line) > 0:
                task_files_list.append(line.strip())

        task_files_list.sort()
        self.log.info(f"Number of tasks: {len(task_files_list)}")
        self.log.info(f"Tasks {task_files_list}")

    def run_tasks(self):
        """ Run the tasks (you must call get_tasks first) on all the machine
        (you must call get_machines first)"""

        # Create a thread for each machine
        threads = []
        for machine in self.available_machines:
            process_thread = threading.Thread(target=self.run_thread_on_ec2_machine,
                                              args=(machine,))
            process_thread.start()
            threads.append(process_thread)

        # Wait for them all to finish
        for thread in threads:
            thread.join()

        self.log.info("Ending runtasks")

    def get_machines(self):
        self.available_machines = util.get_aws_machines(tag_name='ta1', tag_value='cora')
        self.log.info(f"Number of machines {len(self.available_machines)}")
        self.log.info(f"Machines available:  {self.available_machines}")

    def run_xstartup(self):
        ''' Start X Server on all the machines.  Note:  Not parallelized'''
        for machine in self.available_machines:
            cmd = "/home/ubuntu/start_cora_docker.sh"
            return_code = util.shell_run_background_remote(machine, cmd, self.log)
            self.log.debug(f"Tried to start docker on CORA machine {machine}" +
                           f" Result: {return_code}")

    def kill_and_restartX(self):
        for machine in self.available_machines:
            xserver = XServerStartup(machine, self.log)
            xserver.kill_and_restart()

    def change_mcs_config(self):
        for machine in self.available_machines:
            return_code = util.copy_file_to_aws(machine, config_on_local,
                                                self.log,
                                                remote_config_file_directory)
            if not return_code == 0:
                self.log.warn(f"Error copying new config {return_code}")

    def run_check_xorg(self):
        ''' Check X Server on all the machines.  Note:  Not parallelized'''
        for machine in self.available_machines:
            cmd = "docker exec `docker ps -a | grep cora | awk '{print $1}'` ps auxwww | grep Xorg"
            return_code = util.shell_run_command_remote(machine, cmd, self.log)
            self.log.debug(f"X Status on remote machine {machine}" +
                           f" Result: {return_code}")

    def run_test(self):
        self.available_machines = util.get_aws_machines()
        for machine in self.available_machines:
            test_runner = McsTestRunner(machine, self.log)
            test_runner.process()


if __name__ == '__main__':
    run_tasks = CoraRunTasks()
    run_tasks.get_machines()
    run_tasks.get_tasks()

    # Commands to change the Remote machines.  Uncomment them to run them.
    # run_tasks.change_mcs_config()
    # run_tasks.run_xstartup()
    # run_tasks.run_check_xorg()
    # run_tasks.run_test()   # Note, this is not paralleized

    # Command to actually run the tasks.
    run_tasks.run_tasks()

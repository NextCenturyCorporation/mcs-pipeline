# mcs-pipeline

The pipeline makes heavy use of Ray.  Getting familiar with Ray is beneficial.

Ray:
https://docs.ray.io/en/master/index.html

Ray Book of Knowledge: 
https://nextcentury.atlassian.net/wiki/spaces/MCS/pages/2156757749/BoK

****

MCS Project for running evaluations

This code runs scene files on EC2 machines.  Assumptions:
* There is an AMI that exists with the software necessary to run an evaluation.  (Usually this includes performer software, MCS, and MCS AI2THOR)
* The scene files are on the local machine

## Python Environment Setup

From the mcs-pipeline root, create a virtual environment.

```bash
$ python3 -m venv --prompt pipeline venv
$ source venv/bin/activate
(pipeline) $ python -m pip install --upgrade pip setuptools wheel
(pipeline) $ python -m pip install -r requirements.txt
```
## Run Pipeline in AWS

### Run Eval Script

To run an eval, run the following command:
```
aws_scripts/run_eval MODULE path/to/scene/directory [metadata_level]
```

Here is an example:
```
./aws_scripts/run_eval.sh baseline scenes/subset/
```

Note: This script does not stop your cluster.  You should be sure to stop your cluster (See Common Ray Commands) or carefully terminate your AWS instances associated with the cluster.

#### Eval test configuration

In order to test the pipeline and evaluations, the following is helpful:

* In the autoscaler/ray_MODULE_aws.yaml file you plan to use, add your initials or personal ID to the cluster name just so its easier to track in AWS.

* Be sure to stop your cluster and/or terminate the AWS instances when you are done

* Know if/where your results will be upload to avoid conflicts:
  * Files are only uploaded if the MCS config (configs/mcs_config_MODULE_METADATA.ini) has 'evalution=true'
  * Setting the s3_folder to have a suffix of -test is a good idea.  I.E. s3_folder=eval-35-test will 
  * The S3 file names are generated partially by the 'team' and 'evaluation_name' properties.  Prefixing 'evaluation_name' with your initials or a personal ID can make it easier to find your files in S3.  I.E evaluation_name=kdrumm-eval375

#### Script Overview

This script performs the following actions:
* Start a Ray cluster based on the autoscaler/ray_MODULE_aws.yaml file
* Generates a list of scene files and rsyncs that to the head node
* Rsync the following into the head node:
  * pipeline folder
  * deploy_files/MODULE/ folder
  * configs folder
  * provided scenes folder
* submits a ray task via the pipeline_ray.py script with the following parameters:
  * Ray locations config (configs/MODULE_aws.ini)
  * MCS config (configs/mcs_config_MODULE_<METADAT_LEVEL>.ini)
    * Note: by default metadata level is level2

### Common Ray Commands

* Start a cluster: ray up /path/to/config.yaml
* Copy files to head node: ray rsync_up /path/to/config.yaml SOURCE DEST
* Execute shell command on head node: ray exec /path/to/config.yaml "COMMAND"
* Submit a ray python script to the cluster: ray submit /path/to/config.yaml PARAMETER1 PARAMETER2
* Connect to shell on head node: ray attach /path/to/config.yaml
* Shutdown cluster (stops AWS instances): ray down /path/to/config.yaml

## Run Pipeline Locally

TBD

## Project Structure

The pipeline is setup to run different "modules" and uses convention to file the files for each module.  At first, each module will be an evaluation for a specific team, but the goal is to add modules that perform different tasks uses Ray in AWS.

### Folder Structure

* autoscaler - Contains ray configuration for different modules to run in AWS.  The file name convention is ray_MODULE_aws.yaml.  See below and Ray documentation for more details of fields.
* aws_scripts - Contains scripts and text documents to facilitate to running in AWS.
* configs - Contains all necessary configs for each module that will be pushed to Ray head node.  (maybe should be moved to individual deploy_files directories)
* deploy_files - Contains a folder per module named after the module.  All files will be pushed to the home directory of the head node
* pipeline - python code used to run the pipeline that will be pushed to head node

### ray_MODULE_aws.yaml

Some portions of ray_MODULE_aws.yaml are important to how evals are executed and are pointed out here:
* All nodes need permissions to push data to S3.  The head node gets those permissions by default by Ray.  However, the worker nodes by default have no permissions.  To Grant permissions to the worker nodes 2 steps must be taken.
  * Once per AWS account, Add iam:PassRole permission to IAM role assigned to head node (typically ray-autoscaler-v1).  This has been done on MCS's AWS.  This allows the head node to assign IAM roles to the worker nodes.
  * Assign an IAM role to the worker node in ray_MODULE_aws.yaml
    * Create an appropriate IAM role and verify it has an instance profile
    * In ray_MODULE_aws.yaml, under the worker node (usually ray.worker.default) node config, add the following:
    ```
    IamInstanceProfile: 
        Arn: IAM role instance profile ARN
    ```
* In many modules, some files need to be pushed to all nodes including the worker nodes.  The best way we've found to do this is with the file_mounts property.

## Other (rename?) Should we keep these:

### SSH

* Use ray attach, can connect to a shell on the cluster head node.  That is usually more than you need.
* You can also connect to a node via the following:

    <code>ssh -i ~/.ssh/pemfilename.pem username@ec2.2.amazon.com run_script.sh</code>
    
* secrets file, containing the pemfilename and the username.  Copy from pipeline/secrets_template.py 
to pipeline/secrets.py and fill it in.  Do not add to github.
* AWS credentials file.  This should be in the file ~/.aws/credentials.  This will allow you to 
use [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) to get 
EC2 machines.  
* Add the following to your ~/.ssh/config:   <code>StrictHostKeyChecking accept-new</code>
This will allow the EC2 machines to be called without you agreeing to accept them 
manually.

### Logs

Is this still true?

Logs are written into a subdirectory called logs/.   There is one large log file and 
many machine-specific logs, one per machine.  The information is the same, but 
the one large log file can have many machines writing to it at once, so it's 
hard to parse sometimes.  

### Mess Example

Here is an example of running the MESS code.  Warning:  It's not very pretty, but 
we're going to use mess_tasks_runner.py as if it were an interactive tool.  

* Have a running EC2 machine that has the MESS code and the tasks on it, or a small number
* Open mess_task_runner.py in your editor of choice
* Go to the bottom of the file and comment out all the code below getTasks and run it.
* You should see something that looks like:
<pre>2021-03-01 17:16:22,782 main         INFO     Starting runtasks
2021-03-01 17:16:23,017 main         INFO     Number of machines 1
2021-03-01 17:16:23,017 main         INFO     Machines available:  ['ec2-18-206-232-67.compute-1.amazonaws.com']
2021-03-01 17:16:23,020 main         INFO     Number of tasks: 7220
2021-03-01 17:16:23,020 main         INFO     Tasks ['delta_0017_41.json', 'delta_001.....
</pre>
* Start the X Server and verify that it is running:
  * Uncomment the line <code>run_tasks.runXStartup()</code>
  * Run mess_task_runner.py
  * Recomment line
  * Wait 30 seconds 
  * Uncomment the line <code>run_tasks.runCheckXorg()</code>
  * Run mess_task_runner.py
  * Recomment line
  * The result of the above should look like:
<pre>
2021-03-01 17:25:05,148 main         INFO     Sending the following command: ['ssh', '-i', '~/.ssh/clarkdorman-keypair.pem', 'ubuntu@ec2-18-206-232-67.compute-1.amazonaws.com', 'ps auxwww | grep Xorg']
2021-03-01 17:25:05,919 main         INFO     Output: root      3818  0.4  0.0 264508 45724 tty2     Ssl+ 22:24   0:00 /usr/lib/xorg/Xorg -noreset +extension GLX +extension RANDR +extension RENDER -config /tmp/tmpdu2so5p9 :0
2021-03-01 17:25:05,919 main         INFO     Output: ubuntu    3918  0.0  0.0  13316  3228 ?        Ss   22:25   0:00 bash -c ps auxwww | grep Xorg
2021-03-01 17:25:05,919 main         INFO     Output: ubuntu    3920  0.0  0.0  14860  1016 ?        S    22:25   0:00 grep Xorg
2021-03-01 17:25:05,920 main         INFO     Return_code 0
</pre>
* Run a trivial test:
  * This code uses mcs_test.py which starts a controller and runs for 10 steps.  If this 
  is not on the EC2 machine, you will need some other trivial code.  
  * Uncomment the line <code>run_tasks.run_test()</code>
  * Run mess_task_runner.py and re-comment.  
  * Output should look like:
<pre>
2021-03-01 17:31:13,858 main         INFO     Sending the following command: ['ssh', '-i', '~/.ssh/clarkdorman-keypair.pem', 'ubuntu@ec2-18-206-232-67.compute-1.amazonaws.com', 'cd /home/ubuntu/ai2thor-docker && python3 mcs_test.py']
2021-03-01 17:31:17,309 main         INFO     Output: Found path: /home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2.x86_64
2021-03-01 17:31:17,328 main         INFO     Output: Mono path[0] = '/home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2_Data/Managed'
2021-03-01 17:31:17,328 main         INFO     Output: Mono config path = '/home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2_Data/Mono/etc'
2021-03-01 17:31:17,503 main         INFO     Output: Preloaded 'ScreenSelector.so'
2021-03-01 17:31:17,513 main         INFO     Output: Display 0 '0': 1024x768 (primary device).
2021-03-01 17:31:17,559 main         INFO     Output: Logging to /home/ubuntu/.config/unity3d/CACI with the Allen Institute for Artificial Intelligence/MCS-AI2-THOR/Player.log
2021-03-01 17:31:23,718 main         INFO     Output: Image saved to /home/ubuntu/output_image_0.jpg
....
2021-03-01 17:31:23,719 main         INFO     Output: Image saved to /home/ubuntu/output_image_9.jpg
2021-03-01 17:31:23,861 main         INFO     Return_code 0
</pre>
* Try a small run:
  * Copy over an mcs_config.yaml that does not write to the bucket.  Create the mcs_config.yaml in 
  this directory
  * Modify pipeline/mess_config_change.py to make sure that it is looking at the right file locally
  * Uncomment the <code>run_tasks.change_mcs_config()</code> line
  * Run mess_task_runner.py
  * Recomment the line
  * Create a short list of scene files or use <code>tasks_single_tasks.txt</code>.  Set mess_task_runner to use 
  that list of scene files (TASK_FILE_PATH)
  * Uncomment the line <code>run_tasks.runTasks()</code>
  * Run mess_task_runner.py
* Big run:
  * Start lots of machines (~120 or so)
  * Same as the small run, following the same basic steps, one at a time: 
    * Start the X server on each by uncommenting that line and running.  Since this does not  
    run a thread per machine, this might take a couple of minutes
    * Copy over mcs_config.yaml.  Make sure to put in all the information, set 
    the AWS keys, make sure bucket and directory is correct, correct metadata level etc.  Uncomment 
    that line and run.  Again, not parallelized (i.e. thread per machine) so takes a couple 
    of minutes.  
    * Make a file with the correct list of tasks and set the TASK_FILE_PATH to point to it
    * Run the tasks

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research Projects Agency (DARPA) and Naval Information Warfare Center, Pacific (NIWC Pacific) under Contract No. N6600119C4030. Any opinions, findings and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the DARPA or NIWC Pacific.
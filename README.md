# mcs-pipeline

The pipeline makes heavy use of Ray.  Getting familiar with Ray is beneficial.

Ray:
https://docs.ray.io/en/master/index.html

Ray Body of Knowledge: 
https://nextcentury.atlassian.net/wiki/spaces/MCS/pages/2156757749/BoK

****

MCS Project for running evaluations.  Most of this code runs scene files on EC2 machines.  

## Assumptions:
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

### Quickstart Tips

- Make sure you have AWS credentials for MCS set as default.
- For testing, make the follow edits to the autoscaler/xxxx.yaml file you plan to use.

  - Change the cluster name, this will prevent name collsion of EC2s and make finding yours easier.
  - If you want to test how a different library will work, you can add an install command in the setup_commands.
- For testing, find which config/xxxx.ini file that you are using by changing the "evaluation_name" so you can
find the results easier
- If you are going to run "run_eval.sh" you need to be in the python virtal environment first. ```source venv/bin/activate```

#### MCS Config File

When running an eval, there are checks to ensure that the MCS config file used is using the correct naming conventions, so that all the ingest
and UI related functionality will work correctly (these can be turned off for testing):

- **metadata** - has to be either `level1`, `level2`, or `oracle`
- **evaluation_name** - has to be one of the following, in the exact format: `eval_3-75`, `eval_4`, `eval_5`, `eval_6`, `eval_7`, `eval_8`
- **evaluation** - must be set to `true`
- **history_enabled** - must be set to `true`
- **team** - has to be either `mess` (for multiple submissions, `mess1` or `mess2`), `cora` (or `mit` if rerunning a pre-3.75 eval set), `opics`, or `baseline`
- **submission_id** - currently, only needed for MESS submissions (if multiple given). Needs to match the team label (either `1` or `2`)
- **s3_bucket** - should be `evaluation-images`
- **s3_folder** - json output - has to be the folder we store output for the current eval (right now, set to `eval-resources-4` for eval 4)
- **s3_movies_folder**: required post-3.75 (value should be `raw-eval-4` for eval 4) - only mp4 output, MediaConvert will copy all mp4s to the "s3_folder" config property as well 
- **video_enabled** - must be set to `true`

If anything above changes, we will need to make sure those changes are incorporated into the ingest process/UI as needed. 

#### Eval Test Configuration

In order to test the pipeline and evaluations, the following is helpful:

* In the autoscaler/ray_MODULE_aws.yaml file you plan to use, add your initials or personal ID to the cluster name just so its easier to track in AWS.

* Be sure to stop your cluster and/or terminate the AWS instances when you are done.

* Know if/where your results will be uploaded to avoid conflicts:
  * Videos are only saved when `videos_enabled=true`
  * Results are only uploaded if the MCS config (configs/mcs_config_MODULE_METADATA.ini) has `evalution=true`
  * Setting the s3_folder in the MCS config file to have a suffix of -test is a good idea.  I.E. s3_folder=eval-35-test 
  * The S3 file names are generated partially by the `team` and `evaluation_name` properties in the MCS config file.  Prefixing `evaluation_name` with your initials or a personal ID can make it easier to find your files in S3.  I.E evaluation_name=kdrumm-eval375
  * If you'd like to disable logs being uploaded to s3 while testing, set this in your MCS config: `logs_to_s3=false`
  * Make sure MCS config file validation is off if for testing (see commands below).

#### Commands

To run an eval, run the following command on your local development machine (driver):
```
aws_scripts/run_eval MODULE path/to/scene/directory --metadata [metadata_level]
```

There is an optional flag to disable config file validation checks if you are just running tests:
```
aws_scripts/run_eval MODULE path/to/scene/directory --metadata [metadata_level] --disable_validation
```

To capture the output in a log file, add the following after the command.  Tee will allow the output to be sent both to stdout as well as the file.  

```
|& tee <log_filename>
```

You can also use linux pipes to only push to a file.

Here are examples:
```
./aws_scripts/run_eval.sh baseline scenes/subset/


./aws_scripts/run_eval.sh baseline scenes/subset/ |& tee out.txt
```

Note: This script does not stop your cluster.  You should be sure to stop your cluster (See Common Ray Commands) or carefully terminate your AWS instances associated with the cluster. 
When you run "run_eval.sh" it will run all scenes in the directory. Make
a folder somewhere and add the scenes you want to test there.

#### Script Overview

This script performs the following actions:
* Start a Ray cluster based on the autoscaler/ray_MODULE_aws.yaml file
* Generates a list of scene files and rsyncs that to the head node
* Rsync the following into the head node:
  * pipeline folder
  * `deploy_files/MODULE/` folder
  * `configs` folder
  * provided scenes folder
* submits a Ray task via the pipeline_ray.py script with the following parameters:
  * Ray locations config (configs/MODULE_aws.ini)
  * MCS config (configs/mcs_config_MODULE_<METADAT_LEVEL>.ini)
    * Note: by default metadata level is level2

#### Expected Output 

There can be a lot of output and users may want to verify it is working properly

Startup of the Ray cluster can take a couple minutes and include failed attempts to connect to the head node via SSH if the instance was not running

Once the Ray instance is setup and is running a Ray task, you should see output prefixed with:
  `(pid=#####)` or `(pid=#####, ip=###.###.###.###)` for running on the head node or a non-head worker node respectively

Eval tasks with:

```
(pid=16265) Saving mcs config information to /tmp/mcs_config.ini
(pid=16265) Saving scene information to /tmp/cd2344f9-fb75-4dc8-8f8b-6292c9614189.json
```

We currently output a results summary when a task finishes that looks similiar to:

```
file: /home/ubuntu/scenes/tmp/eval_3_5_validation_0001_01.json
Code: 0
Status: Success
Retryable: False
```

### Common Ray Commands

* Start a cluster: `ray up /path/to/config.yaml`
* Copy files to head node: `ray rsync_up /path/to/config.yaml SOURCE DEST`
* Execute shell command on head node: `ray exec /path/to/config.yaml "COMMAND"`
* Submit a Ray python script to the cluster: `ray submit /path/to/config.yaml PARAMETER1 PARAMETER2`
* Monitor cluster (creates tunnel so you can see it locally): `ray dashboard autoscaler/ray_baseline_aws.yaml`
  * Point browser to localhost:8265 (port will be in command output)
* Connect to shell on head node: `ray attach /path/to/config.yaml`
* Shutdown cluster (stops AWS instances): `ray down /path/to/config.yaml`

## Run Pipeline Locally

To run the pipeline locally, make sure to update the paths in configs/test_local.ini to match your local machine. 

"run_script" is currently MCS-pipeline/deploy_files/local/ray_script.sh
"scene_location" is currently MCS/docs/source/scenes/
"scene_list" is a .txt file that you put one scene on each line to run.
"eval_dir" is where the evaluations are written

If you'd like to test upload to S3 from a local machine, also ensure that you have your credentials and config setup correctly in ~/.aws (directions [here] (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)) and update the config in 
configs/mcs_config_local_level2.ini. 

Next you will need to create a "local.yaml" in the "autoscaler" directory. Examples can be found at https://github.com/ray-project/ray/blob/master/python/ray/autoscaler/aws/example-full.yaml

Then run the following:

```
python pipeline_ray.py configs/test_local.ini configs/mcs_config_local_level2.ini --disable_validation --local_only
```

The ray_script.sh here is set to run run_just_pass.py from the MCS project on the list of scenes passed along, but that can be changed to whatever is needed.

## Project Structure

The pipeline is setup to run different "modules" and uses convention to locate files for each module.  At first, each module will be an evaluation for a specific team, but the goal is to add modules that perform different tasks using Ray in AWS.

### Folder Structure

* autoscaler - Contains Ray configuration for different modules to run in AWS.  The file name convention is ray_MODULE_aws.yaml.  See below and Ray documentation for more details of fields.
* aws_scripts - Contains scripts and text documents to facilitate running in AWS.
  * Note: 
* configs - Contains all necessary configs for each module that will be pushed to Ray head node.  (maybe should be moved to individual deploy_files directories)
* deploy_files - Contains a folder per module named after the module.  All files will be pushed to the home directory of the head node
* pipeline - python code used to run the pipeline that will be pushed to head node

### ray_MODULE_aws.yaml

Some portions of ray_MODULE_aws.yaml are important to how evals are executed and are pointed out here:
* All nodes need permissions to push data to S3.  The head node gets those permissions by default from Ray.  However, the worker nodes by default have no permissions.  To Grant permissions to the worker nodes 2 steps must be taken.
  * Once per AWS account, Add iam:PassRole permission to IAM role assigned to head node (typically ray-autoscaler-v1).  This has been done on MCS's AWS.  This allows the head node to assign IAM roles to the worker nodes.
  * Assign an IAM role to the worker node in ray_MODULE_aws.yaml
    * Create an appropriate IAM role and verify it has an instance profile
    * In ray_MODULE_aws.yaml, under the worker node (usually ray.worker.default) node config, add the following:
    ```
    IamInstanceProfile: 
        Arn: IAM role instance profile ARN
    ```
* In many modules, some files need to be pushed to all nodes including the worker nodes.  The best way we've found to do this is with the file_mounts property.

## Additional Information

### SSH

* Use the `ray attach` command to connect to a shell on the cluster head node.
* You can also connect to a node via the following:

    <code>ssh -i ~/.ssh/pemfilename.pem username@ec2.2.amazon.com run_script.sh</code>
    
* secrets file, containing the pemfilename and the username.  Copy from pipeline/secrets_template.py 
to pipeline/secrets.py and fill it in.  Do not add to github.
* We no longer use an AWS credentials file for Ray.  Instances in AWS should be given an IAM role via configurations.
  * When running locally, your system may need an AWS credentials file.  This should be in the file ~/.aws/credentials.  This will allow you to 
use [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) to get 
EC2 machines.  
* Add the following to your ~/.ssh/config:   <code>StrictHostKeyChecking accept-new</code>
This will allow the EC2 machines to be called without you agreeing to accept them 
manually.

### Logs

Logs will be written to the head node and sometimes be pushed to S3.  Details TBD.

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

## Generating RGB Videos

This pipline runs the `run_last_action.py` script (from the `machine_common_sense/scripts/` folder in the MCS repository) to generate videos from the RGB output frames using FFMPEG (with the correct video codecs so the videos are usable on Macs and in web browsers) and upload them to a specific S3 bucket.

1. Update the `s3_bucket`, `s3_folder`, `evaluation_name`, and/or `team_name` in [configs/mcs_config_videos_level1.ini](configs/mcs_config_videos_level1.ini), as needed.
2. Update the `cluster_name` in [autoscaler/ray_videos_aws.yaml](autoscaler/ray_videos_aws.yaml), if needed.
3. Run the command below.
4. Terminate your AWS instances once finished.

```bash
./aws_scripts/run_eval.sh videos <json_data_folder> --metadata level1 --disable_validation
```

## Generating Topdown Videos

This pipline runs the `run_last_action.py` script (from the `machine_common_sense/scripts/` folder in the MCS repository) to generate topdown videos using the plotter inside the machine_common_sense python library and upload them to a specific S3 bucket.

1. Update the `s3_bucket`, `s3_folder`, `evaluation_name`, and/or `team_name` in [configs/mcs_config_topdown_level1.ini](configs/mcs_config_topdown_level1.ini), as needed.
2. Update the `cluster_name` in [autoscaler/ray_topdown_aws.yaml](autoscaler/ray_topdown_aws.yaml), if needed.
3. Run the command below.
4. Terminate your AWS instances once finished.

```bash
./aws_scripts/run_eval.sh topdown <json_data_folder> --metadata level1 --disable_validation
```

## Linting

### Python Code

We are currently using [flake8](https://flake8.pycqa.org/en/latest/) and [autopep8](https://pypi.org/project/autopep8/) for linting and formatting our Python code. This is enforced within the python_api\
 and scene_generator projects. Both are [PEP 8](https://www.python.org/dev/peps/pep-0008/) compliant (besides some inline exceptions), although we are ignoring the following rules:
- **E402**: Module level import not at top of file
- **W504**: Line break occurred after a binary operator

A full list of error codes and warnings enforced can be found [here](https://flake8.pycqa.org/en/latest/user/error-codes.html)

Both have settings so that they should run on save within Visual Studio Code [settings.json](.vscode/settings.json) as well as on commit after running `pre-commit install` (see [.pre-commit-config.yaml]\
(.pre-commit-config.yaml) and [.flake8](.flake8)), but can also be run on the command line:

### Shell Scripts

The shell scripts do not currently have a linter, but it should be added and then 
documented here.

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research Projects Agency (DARPA) and Naval Information Warfare Center, Pacific (NIWC Pacific) under Contract No. N6600119C4030. Any opinions, findings and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the DARPA or NIWC Pacific.

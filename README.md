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
(pipeline) $ pre-commit install
```

## Linting

### Python Code

This project uses [black](https://pypi.org/project/black/) for linting and formatting the Python code.

A full list of error codes and warnings enforced can be found [here](https://flake8.pycqa.org/en/latest/user/error-codes.html)

Both have settings so that they should run on save within Visual Studio Code [settings.json](.vscode/settings.json) as well as on commit after running `pre-commit install` (see [.pre-commit-config.yaml]\
(.pre-commit-config.yaml)), but can also be run on the command line:

```bash
(pipeline) $ pre-commit run --all-files
```

### Shell Scripts

The shell scripts are linted using [shellcheck](https://www.shellcheck.net/).
https://github.com/koalaman/shellcheck
https://github.com/koalaman/shellcheck#installing

There's a VS Code extension as well.
https://marketplace.visualstudio.com/items?itemName=timonwong.shellcheck


## Run Pipeline in AWS

### Run Eval Script

### Quickstart Tips

- Make sure you have AWS credentials for MCS set as default.
- If you are going to run "run_eval.py" you need to be in the python virtal environment first. ```source venv/bin/activate```

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
- **s3_folder** - json output - has to be the folder we store output for the current eval (right now, set to `eval-resources-5` for eval 5)
- **s3_movies_folder**: required post-3.75 (value should be `raw-eval-5` for eval 5) - only mp4 output, MediaConvert will copy all mp4s to the "s3_folder" config property as well
- **video_enabled** - must be set to `true`

If anything above changes, we will need to make sure those changes are incorporated into the ingest process/UI as needed.

#### Eval Test Configuration

In order to test the pipeline and evaluations, the following is helpful:

* Be sure to stop your cluster and/or terminate the AWS instances when you are done.

* Know if/where your results will be uploaded to avoid conflicts:
  * Videos are only saved when `videos_enabled: true`
  * Results are only uploaded if `evalution_bool: true`
  * Setting the s3_folder in the MCS config file to have a suffix of -test is a good idea.  I.E. `s3_folder: eval-35-test`
  * The S3 file names are generated partially by the `team` and `evaluation_name` properties in the MCS config file.  Prefixing `evaluation_name` with your initials or a personal ID can make it easier to find your files in S3.  I.E eval_name: kdrumm-eval375
  * If you'd like to disable logs being uploaded to s3 while testing, change `logs_to_s3` to be `false` in `mako/templates/mcs_config_template.ini`
  * Make sure MCS config file validation is off if for testing (see commands below).

#### Eval orchestration script

An eval can be run via the run_eval.py script.  Run script for usage.

The script will require a YAML configuration file

Config File API (yaml):
    The job of this script is to create a list of 'eval-group' parameters which is a set of parameters
    to run a single ray job for an eval.  The parameters for an eval group are below, but in general it is
    used to generate set of files, at a certain metadata level, with some other run parameters.
    To do this, we use a config file to generate these eval groups, where most values are lists where each entry
    is a single option.  The script will create eval-groups using each combination of options to create many
    permutation of these values.

    The config file has two high level objects:
    base - an 'eval-group' object that contains default values for any listed 'eval-groups'.
    eval-groups - contains a list of 'eval-group' objects.  Each grouping will create a number of sets as described below.

    An eval-group is a group of values used to create all permutations of eval sets.
    Eval sets are parameters and scenes to run a single task in ray for an eval.

    values for an eval-group:
      varset - list of variable files that are used for template generation.  Earlier
        files are override by later values if they contain the same variable.  This is
        the only array where all values are used for each eval-set instead of each
        value creating more permutations.  Varset in the 'eval-groups' will override, not
        concatentate, those in the 'base' variable.

        varsets will automatically add 'default' and 'user' to the beginning of the list.
        'user' is only added if the file exists. The 'user' varset is to be added for
        user specific variables like naming clusters with something like
        'clusterUser: -myName'
      metadata - single or list of metadata levels.  Each metadata level will create more
        permutations of the eval-sets
      parent-dir - Must be used mutually exclusively with 'dirs'.   This points to a directory
        where each subdirectory should contain scenes and will be used to create permutations
        of eval-sets
      dirs - Must be used mutually exclusively with 'parent-dir'.  Single or list of directories
        which each should contain scenes to be used to create permutations of eval-sets.


    Example:
    base:
        varset: ['opics', 'personal']
    eval-groups:
        - metadata: ['level1', 'level2']
          parent-dir: 'mako-test/parent'
        - metadata: ['level2', 'oracle']
          dirs: ['mako-test/dirs/dir1', 'mako-test/dirs/dir2']

    This example will use the 'opics.yaml' and 'personal.yaml' files in the 'variables' directory to fill the templates.
    It expects to have a directory 'mako-test/parent/' which has one or more subdirectories filled with scenes.  It also
    expects the following directories with scene files: 'mako-test/dirs/dir1', 'mako-test/dirs/dir2'.

#### Commands

This script assumes you have the ts.  you can install ts via `sudo apt install moreutils`
This script assumes you have the unbuffer.  you can install ts via `sudo apt install expect`

Python Script:

To run a single ray run, run the following command on your local development machine (driver):
```
python run_eval_single.py -v opics -s eval4-validation-subset/group3 -m level2
```

To run a full eval from a configured file:
```
python run_eval.py -d -n 1 -c mako/eval-4-subset.yaml
```

See the scripts help text for additional options such as disabling validation, using dev validation and redirecting logs to STDOUT, and dry run.

Configuration files and a resume.yaml will be written in the .tmp_pipeline_ray directory in a timestamped folder for your run.  To resume an interrupted run or a run with failures, you can change the -c option to the resume.yaml found here.

#### Log Parsing

The `run_eval` script is always run with 'ts -s', and the output logs can be parsed by `pipeline/log_parser.py`.  This command will split the logs into logs per working node and then use some regex to report some metrics on how long different portions of a run took.  At the moment, the script output is somewhat rough and it only has good support for tracking opics logging.

#### Script Overview

The run_eval**.py scripts performs the following actions and may run them multiple times:
* Start a Ray cluster based on the mako configs
* Generates a list of scene files and rsyncs that to the head node
* Rsync the following into the head node:
  * pipeline folder
  * `deploy_files/MODULE/` folder
  * `configs` folder
  * provided scenes folder
* submits a Ray task via the pipeline_ray.py script with the following parameters:
  * Ray locations config (configs/MODULE_aws.ini)
  * MCS config (mako/templates/mcs_config_template.ini)
    * Note: by default metadata level is level2

#### Ray Expected Output

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
* Monitor cluster (creates tunnel so you can see it locally): `ray dashboard /path/to/config.yaml`
  * Point browser to localhost:8265 (port will be in command output)
* Connect to shell on head node: `ray attach /path/to/config.yaml`
* Shutdown cluster (stops AWS instances): `ray down /path/to/config.yaml`

## Run Pipeline Locally

To run the pipeline locally, make sure to update the paths in configs/test_local.ini to match your local machine.

- "run_script" will be `<mcs-pipeline>/deploy_files/local/ray_script.sh`
- "scene_location" is where the JSON scene files are located; you can find some sample scenes in the `docs/source/scenes/` folder in the `MCS` GitHub repository
- "scene_list" is a .txt file that you put one scene on each line to run.
- "eval_dir" is where the evaluations are written

If you'd like to test upload to S3 from a local machine, also ensure that you have your credentials and config setup correctly in ~/.aws (directions [here] (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)) and update the config in configs/mcs_config_local_level2.ini.

Then run the following:

```
python ray_scripts/pipeline_ray.py configs/test_local.ini configs/mcs_config_local_level2.ini --disable_validation --local_only
```

The ray_script.sh here is set to run run_just_pass.py from the MCS project on the list of scenes passed along, but that can be changed to whatever is needed.

## Project Structure

The pipeline is setup to run different "modules" and uses convention to locate files for each module.  At first, each module will be an evaluation for a specific team, but the goal is to add modules that perform different tasks using Ray in AWS.

### Folder Structure

* configs - Contains all necessary configs for each module that will be pushed to Ray head node.
* deploy_files - Contains a folder per module named after the module.  All files will be pushed to the home directory of the head node.
* mako/templates/mcs_config_template.ini - Template for the MCS configuration for running modules on AWS.
* mako/templates/ray_template_aws.yaml - Template for the Ray configuration for running modules on AWS. See below and Ray documentation for more details of fields.
* mako/variables/ - Contains specific pipeline configuration for running individual modules.
* pipeline - Python code used to run the pipeline that will be pushed to head node.

### Ray Template

Some portions of `ray_template_aws.yaml` are important to how evals are executed and are pointed out here:
* We use a default IamInstanceProfile to give our worker nodes permission to push data to S3.
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

1. Update the `s3_bucket`, `s3_folder`, and/or `eval_name`, in [mako/variables/videos.yaml](mako/variables/videos.yaml), as needed.
2. Create a mako config with a `varset` of `videos` and a `metadata` of `level1`. See the example below.

```yaml
base:
  varset: ['videos']
  metadata: ['level1']
eval-groups:
  - dirs: ['my_folder/']
```

3. Run the command below.
4. Terminate your AWS instances once finished.

```bash
python run_eval.py --disable_validation -n 1 -c <mako_config> -u <cluster_name> --num_retries 5
```

## Generating Topdown Videos

This pipline runs the `run_last_action.py` script (from the `machine_common_sense/scripts/` folder in the MCS repository) to generate topdown videos using the plotter inside the machine_common_sense python library and upload them to a specific S3 bucket.

1. Update the `s3_bucket`, `s3_folder`, and/or `eval_name`, in [mako/variables/topdowns.yaml](mako/variables/topdowns.yaml), as needed.
2. Create a mako config with a `varset` of `topdowns` and a `metadata` of `level1`. See the example below.

```yaml
base:
  varset: ['topdowns']
  metadata: ['level1']
eval-groups:
  - dirs: ['my_folder/']
```

3. Run the command below.
4. Terminate your AWS instances once finished.

```bash
python run_eval.py --disable_validation -n 1 -c <mako_config> -u <cluster_name> --num_retries 5
```

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research Projects Agency (DARPA) and Naval Information Warfare Center, Pacific (NIWC Pacific) under Contract No. N6600119C4030. Any opinions, findings and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the DARPA or NIWC Pacific.

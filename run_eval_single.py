import argparse
import pathlib

from run_eval import EvalParams, EvalRun, execute_shell, get_now_str


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a single ray job from files from a single directory."
    )
    parser.add_argument(
        "--local_scene_dir",
        "-s",
        default=None,
        required=True,
        help="Local scene directory to be used for a single run.",
    )
    parser.add_argument(
        "--local_template_dir",
        "-b",
        default="mako",
        help="Local directory containing 'variables' and 'templates' directory for creating config files.",
    )
    parser.add_argument(
        "--dev_validation",
        default=False,
        action="store_true",
        help="Whether or not to validate for development instead of production",
    )
    parser.add_argument(
        "--disable_validation",
        default=False,
        action="store_true",
        help="Whether or not to skip validatation of MCS config file",
    )
    parser.add_argument(
        "--redirect_logs",
        "-r",
        default=False,
        action="store_true",
        help="Whether or not to copy output logs to stdout",
    )
    parser.add_argument(
        "--metadata",
        "-m",
        default="level2",
        help="Sets the metadata level for a single run.",
    )
    parser.add_argument(
        "--team",
        "-t",
        default=None,
        help="Sets the team a single run.  If set in varset, this is not necessary, but this value will override.",
    )
    # At one point, I had varset as required.  However, if the user wants to create config file
    # without variables, they can use a template that is the config file itself without variables.
    parser.add_argument(
        "--varset",
        "-v",
        type=str,
        nargs="+",
        default=[],
        help="Sets list of variable set files that should be read.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    now = get_now_str()
    vars = "-".join(args.varset)
    team = args.team
    override = {"team": team} if team else {}
    log_team = f"{team}-" if team else ""
    log_dir_path = "logs-single-run"
    log_dir = pathlib.Path(log_dir_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = f"{log_dir_path}/{now}-{log_team}{vars}-{args.metadata}.log"
    ep = EvalParams(
        args.varset, args.local_scene_dir, args.metadata, override=override
    )
    execute_shell("echo Starting `date`", log_file)
    run = EvalRun(
        ep,
        disable_validation=args.disable_validation,
        dev_validation=args.dev_validation,
        log_file=log_file,
        output_logs=args.redirect_logs,
    )
    run.run_eval()
    execute_shell("echo Finishing `date`", log_file)
    execute_shell(f"ray down -y {run.ray_cfg_file.as_posix()}", log_file)

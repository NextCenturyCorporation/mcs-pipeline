import argparse

from run_eval import EvalParams, get_now_str, run_eval


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run multiple eval sets containing scenes using ray.  There are two modes.  " +
        "One uses the '--config_file' option.  The other uses the '--local_scene_dir' option.")
    parser.add_argument(
        "--dev_validation", "-d",
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
        "--redirect_logs", "-r",
        default=False,
        action="store_true",
        help="Whether or not to copy output logs to stdout",
    )
    parser.add_argument(
        "--local_scene_dir", "-s",
        default=None,
        help="Local scene directory to be used for a single run.",
    )
    parser.add_argument(
        "--metadata", "-m",
        default='level2',
        help="Sets the metadata level for a single run.",
    )
    parser.add_argument(
        "--varset", "-v", type=str, nargs='+',
        help="Sets list of variable set files that should be read.",
    )
    return parser.parse_args()


# TODO MCS-1066 Finish and test
if __name__ == "__main__":
    args = parse_args()
    now = get_now_str()
    vars = "-".join(args.varset)
    log_file = f"logs/{now}-{vars}-{args.metadata}.log"
    ep = EvalParams(args.varset, args.local_scene_dir, args.metadata)
    run_eval(ep.varset, ep.local_scene_dir, ep.metadata,
             disable_validation=args.disable_validation,
             dev_validation=args.dev_validation,
             resume=args.resume, log_file=log_file, output_logs=args.redirect_logs)

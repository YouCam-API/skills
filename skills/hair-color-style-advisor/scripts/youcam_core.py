#!/usr/bin/env python3
"""youcam_core.py is the shared CLI that every YouCam (Perfect Corp) skill uses to call the API.

Setup:
    Run the "setup" command first. It creates a local virtual environment and installs
    everything the skill needs.

Auth:
    Set the YOUCAM_API_KEY environment variable, or create a credentials.json file (in the
    skill's root, next to SKILL.md) containing {"api_key": "..."}. The env var is used first
    if both are present. If neither is set, the command & API call fails.

Example:
    python youcam_core.py setup
    python youcam_core.py validate-key
    python youcam_core.py credits
    python youcam_core.py cost --feature skin-analysis
    python youcam_core.py run --feature skin-analysis --src_file a.jpg \
        --param format=json --param dst_actions='["hd_pore","hd_skin_type"]'
    python youcam_core.py status --feature skin-analysis --task_id <task_id>
"""

import argparse
import json
import subprocess
import sys

from constants import _DEFAULT_MAX_POLLS, _DEFAULT_POLL_INTERVAL
from youcam_api import get_credits, get_feature_cost, get_key, load_contract
from youcam_init import _MISSING_DEPS, _dependency_error, requests, setup_env
from youcam_tasks import UploadBatchError, _parse_params, poll, run


def _print_task_error(result: dict) -> int:
    """Print a failed task's payload in the standard {error, hint, details} shape.

    Returns:
        int: Exit code 1.
    """
    print(
        json.dumps(
            {
                "error": "Task failed.",
                "hint": "Check the request parameters against the feature's API doc; "
                "see `details` for the API's raw error payload.",
                "details": result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1


def main() -> int:
    """Parse CLI arguments and dispatch to the matching command.

    Returns:
        int: Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(description="Run and check YouCam AI features from the command line")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    subparsers.add_parser(
        "setup",
        help="Create a local .venv and install requirements.txt. "
        "Run this first or whenever a dependency is missing",
    )
    subparsers.add_parser("validate-key")
    subparsers.add_parser("credits")
    cost_parser = subparsers.add_parser("cost")
    cost_parser.add_argument("--feature")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--feature", required=True)
    run_parser.add_argument("--src_file", help="Local path or URL")
    run_parser.add_argument(
        "--src_files", nargs="+", help="Multiple local paths and/or URLs, e.g. 3 angle photos"
    )
    run_parser.add_argument(
        "--ref_file", help="Local path or URL, e.g. hair-transfer/cloth-v4's reference image"
    )
    run_parser.add_argument("--ref_files", nargs="+", help="Multiple local paths and/or URLs")
    run_parser.add_argument("--param", action="append")
    run_parser.add_argument(
        "--version", help="Override the version, once the LLM learns of a newer one from the live doc"
    )
    run_parser.add_argument("--interval", type=float, default=_DEFAULT_POLL_INTERVAL)
    run_parser.add_argument("--max_polls", type=int, default=_DEFAULT_MAX_POLLS)
    status_parser = subparsers.add_parser(
        "status", help="Check a previously created task's status/result by its task_id"
    )
    status_parser.add_argument("--feature", required=True)
    status_parser.add_argument("--task_id", required=True)
    status_parser.add_argument(
        "--version", help="Override the version, once the LLM learns of a newer one from the live doc"
    )
    status_parser.add_argument("--interval", type=float, default=_DEFAULT_POLL_INTERVAL)
    status_parser.add_argument(
        "--max_polls",
        type=int,
        default=1,
        help="Number of status checks; defaults to 1 (check once instead of blocking until done)",
    )
    args = parser.parse_args()

    if args.cmd == "setup":
        try:
            return setup_env()
        except subprocess.CalledProcessError as exc:
            print(
                json.dumps(
                    {
                        "error": "setup_failed",
                        "hint": "Re-run `python youcam_core.py setup`, or run the failing "
                        "command manually to see its full output.",
                        "details": f"command={exc.cmd!r} returncode={exc.returncode}",
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 1

    try:
        if _MISSING_DEPS:
            return _dependency_error()

        key = get_key()
        if not key:
            return 2  # get_key() error messages

        if args.cmd == "validate-key":
            print(json.dumps({"key": "valid", **get_credits(key)}, ensure_ascii=False, indent=2))
        elif args.cmd == "credits":
            print(json.dumps(get_credits(key), ensure_ascii=False, indent=2))
        elif args.cmd == "cost":
            print(json.dumps(get_feature_cost(key, args.feature), ensure_ascii=False, indent=2))
        elif args.cmd == "run":
            result = run(
                args.feature,
                src_file=args.src_files or args.src_file,
                ref_file=args.ref_files or args.ref_file,
                params=_parse_params(args.param),
                key=key,
                version=args.version,
                interval=args.interval,
                max_polls=args.max_polls,
            )
            if result.get("task_status") == "error":
                return _print_task_error(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.cmd == "status":
            contract = load_contract(args.feature)
            result = poll(
                contract, args.feature, args.task_id, key, args.version, args.interval, args.max_polls
            )
            if result.get("task_status") == "error":
                return _print_task_error(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except requests.HTTPError as exc:
        print(
            json.dumps(
                {
                    "error": f"HTTP {exc.response.status_code} from the YouCam API.",
                    "hint": "Check the request parameters, feature name, and version against "
                    "the API doc; see `details` for the raw response body.",
                    "details": exc.response.text,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    except UploadBatchError as exc:
        print(
            json.dumps(
                {
                    "error": "Some uploads failed while resolving src_file/ref_file.",
                    "hint": "Retry with just the failed sources; see `uploaded` for what "
                    "already succeeded and `failed` for what needs fixing.",
                    "uploaded": exc.uploaded,
                    "failed": exc.failed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "hint": "See `details` for the underlying error message.",
                    "details": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

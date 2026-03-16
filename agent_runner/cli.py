"""Agent Runner CLI entry point."""

from __future__ import annotations

import argparse
import sys

from agent_runner.config import Config
from agent_runner.lock import LockError
from agent_runner.runner import execute_run


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agent Runner: drone controller evaluation",
    )
    parser.add_argument("--goal", required=True, help="Goal for the controller optimization")
    parser.add_argument("--constraints", default="", help="Constraints for patch generation")
    parser.add_argument("--repo-url", default=None, help="Override REPO_URL env var")
    parser.add_argument("--base-ref", default=None, help="Override BASE_REF env var")
    parser.add_argument(
        "--patch-file",
        default=None,
        help="Path to a manually generated patch.diff. Overrides PATCH_FILE env var.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = Config.from_env()

    if args.repo_url:
        config.repo_url = args.repo_url
    if args.base_ref:
        config.base_ref = args.base_ref
    if args.patch_file:
        config.patch_file = args.patch_file

    if not config.repo_url:
        print("Error: REPO_URL env var or --repo-url is required.", file=sys.stderr)
        sys.exit(1)
    if not config.base_ref:
        print("Error: BASE_REF env var or --base-ref is required.", file=sys.stderr)
        sys.exit(1)
    if not config.patch_file and not config.openai_api_key:
        print(
            "Error: either PATCH_FILE/--patch-file or OPENAI_API_KEY env var is required.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        run_id = execute_run(
            config=config,
            goal=args.goal,
            constraints=args.constraints,
        )
        print(f"Run completed: {run_id}")
        print(f"Artifacts: {config.artifacts_root}/runs/{run_id}/")
    except LockError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

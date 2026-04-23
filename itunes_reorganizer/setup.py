"""Setup wizard: create config.json interactively or via command-line flags."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config


def _prompt_path(prompt: str, must_exist: bool = True, is_dir: bool = True) -> Path:
    """Prompt user for a path, validating it exists."""
    while True:
        raw = input(f"  {prompt}: ").strip().strip("'\"")
        if not raw:
            print("    Please enter a path.")
            continue
        path = Path(raw).expanduser().resolve()
        if must_exist and not path.exists():
            print(f"    Path does not exist: {path}")
            continue
        if must_exist and is_dir and not path.is_dir():
            print(f"    Not a directory: {path}")
            continue
        return path


def _prompt_choice(prompt: str, choices: list[str], default: int = 0) -> str:
    """Prompt user to choose from a list of options."""
    print(f"  {prompt}")
    for i, choice in enumerate(choices):
        marker = " (default)" if i == default else ""
        print(f"    {i + 1}. {choice}{marker}")
    while True:
        raw = input(f"  Choose [1-{len(choices)}] (default {default + 1}): ").strip()
        if not raw:
            return choices[default]
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print(f"    Please enter a number between 1 and {len(choices)}")


def _prompt_yes_no(prompt: str, default: bool = False) -> bool:
    """Prompt user for yes/no."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"  {prompt} {suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("    Please enter y or n.")


def interactive_setup() -> Config:
    """Run interactive setup wizard."""
    print("\niTunes Reorganizer — Setup Wizard")
    print("=" * 40)
    print()

    print("1. Source directory (your music library):")
    source = _prompt_path("Path", must_exist=True, is_dir=True)

    print("\n2. Destination directory (reorganized output):")
    dest = _prompt_path("Path", must_exist=False, is_dir=True)

    print("\n3. Operation mode:")
    operation = _prompt_choice(
        "How should files be handled?",
        ["copy", "move"],
        default=0,
    )

    print("\n4. Dry-run mode:")
    dry_run = _prompt_yes_no("Run in dry-run mode? (no changes to filesystem)", default=True)

    print("\n5. Fallback to track artist:")
    fallback = _prompt_yes_no(
        "Use track artist when album artist is missing?",
        default=False,
    )

    return Config(
        source_root=source,
        destination_root=dest,
        dry_run=dry_run,
        operation=operation,
        fallback_to_artist=fallback,
    )


def non_interactive_setup(args: argparse.Namespace) -> Config:
    """Create config from command-line arguments."""
    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()

    if not source.exists():
        print(f"Error: Source directory does not exist: {source}", file=sys.stderr)
        sys.exit(1)
    if not source.is_dir():
        print(f"Error: Source path is not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    return Config(
        source_root=source,
        destination_root=dest,
        dry_run=args.dry_run,
        operation=args.operation,
        fallback_to_artist=args.fallback_to_artist,
    )


def main():
    parser = argparse.ArgumentParser(
        description="iTunes Reorganizer — Setup Wizard",
    )
    parser.add_argument("--source", help="Source music directory")
    parser.add_argument("--dest", help="Destination directory")
    parser.add_argument("--operation", choices=["copy", "move"], default="copy", help="File operation (default: copy)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run mode (default: true)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Disable dry-run mode")
    parser.add_argument("--fallback-to-artist", action="store_true", default=False, help="Use track artist when album artist is missing")
    parser.add_argument("--output", default="config.json", help="Output config file path (default: config.json)")

    args = parser.parse_args()

    # If source and dest are provided, run non-interactively
    if args.source and args.dest:
        config = non_interactive_setup(args)
    else:
        config = interactive_setup()

    output_path = Path(args.output)
    config.save(output_path)
    print(f"\nConfig saved to: {output_path.resolve()}")
    print(f"\nTo run: python -m itunes_reorganizer.main {output_path}")


if __name__ == "__main__":
    main()

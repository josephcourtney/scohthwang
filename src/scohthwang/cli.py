"""Minimal command-line entry point for package smoke checks."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from scohthwang import __all__ as public_api
from scohthwang import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="scohthwang",
        description="Inspect the installed scohthwang package.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--list-api",
        action="store_true",
        help="print the public API symbols exported by scohthwang",
    )
    return parser


def cli(argv: Sequence[str] | None = None) -> int:
    """Run the ``scohthwang`` command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_api:
        print("\n".join(public_api))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

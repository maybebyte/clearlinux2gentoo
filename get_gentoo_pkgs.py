#!/usr/bin/env python3
"""
Script to extract and organize Gentoo packages from the Portage database.
This creates a formatted text file with packages grouped by category.
"""
import os
import sys
import argparse
from collections import defaultdict
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_OUTPUT_FILE = os.path.join(DATA_DIR, "gentoo_pkgs.txt")

try:
    import portage
except ImportError:
    ERROR_MSG = """
Error: The 'portage' module could not be found.
Are you running this script on something other than Gentoo?
"""
    sys.stderr.write(ERROR_MSG.strip() + "\n")
    sys.exit(1)


def get_packages() -> Dict[str, List[str]]:
    """Retrieve all packages from the Portage database.

    Returns:
        Dict[str, List[str]]: A dictionary mapping categories to lists of packages.
    """
    packages = defaultdict(list)

    try:
        all_packages = portage.db[portage.root]["porttree"].dbapi.cp_all()

        for cp in all_packages:
            if "/" in cp:
                category, pkg = cp.split("/", 1)
                packages[category].append(pkg)
    except Exception as e:
        print(f"Error accessing Portage database: {e}", file=sys.stderr)
        sys.exit(1)

    return packages


def write_packages(packages: Dict[str, List[str]], output_file: str) -> None:
    """Write packages to the specified file in category/package format.

    Args:
        packages: Dictionary mapping categories to lists of packages.
        output_file: Path to the output file.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for category, pkgs in sorted(packages.items()):
                for pkg in sorted(pkgs):
                    f.write(f"{category}/{pkg}\n")
    except OSError as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


def parse_arguments():
    """Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Extract Gentoo packages from Portage database"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point of the script, handles package extraction and writing.

    Returns:
        int: Exit code (0 for success, 1 for errors).
    """
    args = parse_arguments()

    packages = get_packages()
    if not packages:
        print("Warning: No packages found to write", file=sys.stderr)
        return 1

    write_packages(packages, args.output)
    print(f"Successfully wrote package list to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

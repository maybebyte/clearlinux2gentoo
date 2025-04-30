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

DEFAULT_OUTPUT_FILE = os.path.join("data", "gentoo_pkgs.txt")

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
        Dict[str, List[str]]: A dictionary mapping categories to lists of
        packages.

    Raises:
        RuntimeError: If the Portage database is not accessible or empty.
    """
    packages = defaultdict(list)
    try:
        all_packages = portage.db[portage.root]["porttree"].dbapi.cp_all()
        if not all_packages:
            raise RuntimeError("No packages found in Portage database.")

        for cp in all_packages:
            if "/" not in cp:
                continue
            try:
                category, pkg = cp.split("/", 1)
                packages[category].append(pkg)
            except ValueError:
                print(
                    f"Warning: Skipping malformed package entry: {cp}",
                    file=sys.stderr,
                )
    except (KeyError, AttributeError) as e:
        raise RuntimeError(f"Cannot access Portage database: {e}") from e

    return packages


def write_packages(packages: Dict[str, List[str]], output_file: str) -> None:
    """Write packages to the specified file in category/package format.

    Args:
        packages: Dictionary mapping categories to lists of packages.
        output_file: Path to the output file.

    Raises:
        IOError: If the output file cannot be written to.
    """
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    except PermissionError as e:
        raise IOError(f"Cannot create output directory: {e}") from e

    with open(output_file, "w", encoding="utf-8") as f:
        for category, pkgs in sorted(packages.items()):
            for pkg in sorted(pkgs):
                f.write(f"{category}/{pkg}\n")


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
    output_file = args.output

    try:
        packages = get_packages()
        if not packages:
            print("Warning: No packages found to write", file=sys.stderr)
            return 0

        write_packages(packages, output_file)
        print(f"Successfully wrote package list to {output_file}")
        return 0
    except (IOError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()

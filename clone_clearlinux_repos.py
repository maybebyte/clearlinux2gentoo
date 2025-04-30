#!/usr/bin/env python3
"""
Repository Cloner - Clones GitHub repositories from clearlinux-pkgs user
based on package names from mapping JSON file
"""

import json
import os
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_MAPPING_FILE = os.path.join(DATA_DIR, "pkg_mapping.json")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "clearlinux-repos")
DEFAULT_MAX_WORKERS = 5

GITHUB_ORG_URL = "https://github.com/clearlinux-pkgs"


def load_mapping_data(mapping_file: str) -> Dict[str, Any]:
    """
    Load package mapping data from JSON file.

    Args:
        mapping_file: Path to JSON mapping file

    Returns:
        Dictionary containing package mapping data
    """
    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Mapping file '{mapping_file}' not found")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in mapping file '{mapping_file}'")
        exit(1)


def clone_repository(pkg_name: str, output_dir: str) -> bool:
    """
    Clone a repository for a specific package.

    Args:
        pkg_name: Package name (used as repository name)
        output_dir: Directory to clone repositories into

    Returns:
        True if clone was successful, False otherwise
    """
    repo_url = f"{GITHUB_ORG_URL}/{pkg_name}"
    repo_dir = os.path.join(output_dir, pkg_name)

    if os.path.exists(repo_dir):
        print(f"Skipping {pkg_name}: directory already exists")
        return False

    try:
        os.makedirs(output_dir, exist_ok=True)

        print(f"Cloning {pkg_name}...")
        subprocess.run(
            ["git", "clone", repo_url, repo_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(
            f"Failed to clone {pkg_name}: {e.stderr.decode('utf-8').strip()}"
        )
        return False


def clone_repositories(
    pkg_names: List[str], output_dir: str, max_workers: int
) -> Dict[str, bool]:
    """
    Clone multiple repositories in parallel.

    Args:
        pkg_names: List of package names to clone
        output_dir: Directory to clone repositories into
        max_workers: Maximum number of parallel workers

    Returns:
        Dictionary mapping package names to clone success status
    """
    results = {}

    os.makedirs(output_dir, exist_ok=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(clone_repository, pkg_name, output_dir): pkg_name
            for pkg_name in pkg_names
        }

        for future in futures:
            pkg_name = futures[future]
            try:
                results[pkg_name] = future.result()
            except Exception as e:
                print(f"Exception when cloning {pkg_name}: {e}")
                results[pkg_name] = False

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories from clearlinux-pkgs based on package mapping"
    )
    parser.add_argument(
        "-m",
        "--mapping-file",
        default=DEFAULT_MAPPING_FILE,
        help=f"Path to JSON mapping file (default: {DEFAULT_MAPPING_FILE})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to clone repositories into (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-w",
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Maximum number of parallel cloning workers (default: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "-f", "--filter", help="Only clone packages containing this substring"
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Print repositories that would be cloned without actually cloning them",
    )

    args = parser.parse_args()

    mapping_data = load_mapping_data(args.mapping_file)

    pkg_names = [
        name
        for name, mapping in mapping_data.items()
        if mapping.get("gentoo_match")
    ]
    print(f"Found {len(pkg_names)} packages with Gentoo mappings")

    if args.filter:
        pkg_names = [name for name in pkg_names if args.filter in name]
        print(
            f"Filtered to {len(pkg_names)} packages containing '{args.filter}'"
        )

    pkg_names.sort()

    if args.dry_run:
        print(f"Would clone {len(pkg_names)} repositories:")
        for pkg_name in pkg_names:
            print(f"  {pkg_name}")
        return

    print(f"Cloning {len(pkg_names)} repositories to {args.output_dir}...")
    results = clone_repositories(pkg_names, args.output_dir, args.max_workers)

    success_count = sum(1 for success in results.values() if success)
    print(
        f"\nSummary: Successfully cloned {success_count} out of {len(pkg_names)} repositories"
    )

    failed = [pkg_name for pkg_name, success in results.items() if not success]
    if failed:
        print(f"\nFailed to clone {len(failed)} repositories:")
        for pkg_name in failed:
            print(f"  {pkg_name}")


if __name__ == "__main__":
    main()

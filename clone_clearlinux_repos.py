#!/usr/bin/env python3
"""
Repository Cloner - Clones GitHub repositories from clearlinux-pkgs user
based on package names from mapping JSON file
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

# Constants for configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_MAPPING_FILE = os.path.join(DATA_DIR, "pkg_mapping.json")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "clearlinux-repos")
DEFAULT_MAX_WORKERS = 5

GITHUB_ORG_URL = "https://github.com/clearlinux-pkgs"

# Global variables for interrupt handling
executor = None
futures_to_cancel = set()


def signal_handler(signum, _frame):
    """
    Handle interruption signals cleanly by canceling pending tasks.

    Args:
        signum: Signal number
        _frame: Current stack frame (unused)
    """
    print(f"\nReceived signal {signum}, gracefully shutting down...")

    global executor, futures_to_cancel
    if executor:
        # Cancel all pending futures
        for future in futures_to_cancel:
            if not future.done():
                future.cancel()

        # Shutdown the executor without waiting for pending tasks
        # Python 3.9+ has cancel_futures parameter
        if sys.version_info >= (3, 9):
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=False)

    print("Shutdown complete. Exiting...")
    sys.exit(0)


def load_mapping_data(mapping_file: str) -> Dict[str, Any]:
    """
    Load package mapping data from JSON file.

    Args:
        mapping_file: Path to JSON mapping file

    Returns:
        Dictionary containing package mapping data

    Raises:
        SystemExit: If the file is not found or contains invalid JSON
    """
    try:
        with open(mapping_file, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except FileNotFoundError:
        print(f"Error: Mapping file '{mapping_file}' not found")
        print("Please check the file path or create the mapping file first.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in mapping file '{mapping_file}'")
        print("Please verify that the file contains valid JSON data.")
        sys.exit(1)


def run_command(
    cmd: List[str], cwd: str, text: bool = False
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command with proper signal handling.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory
        text: Whether to return text output instead of bytes

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit
        code
    """
    # Use start_new_session to ensure process group separation
    # (better signal handling)
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        start_new_session=True,
    )


def initialize_git_repo(repo_dir: str, repo_url: str) -> None:
    """
    Initialize a new Git repository and configure the remote.

    Args:
        repo_dir: Local directory for the repository
        repo_url: URL of the remote repository
    """
    # Initialize a new git repository
    run_command(["git", "init"], repo_dir)

    # Add the remote origin
    run_command(["git", "remote", "add", "origin", repo_url], repo_dir)


def configure_sparse_checkout(repo_dir: str) -> None:
    """
    Configure the repository for sparse checkout to minimize data transfer.

    Args:
        repo_dir: Local directory for the repository
    """
    # Enable sparse checkout
    run_command(["git", "config", "core.sparseCheckout", "true"], repo_dir)

    # Configure which files to checkout (only options.conf in this case)
    sparse_checkout_path = os.path.join(repo_dir, ".git/info/sparse-checkout")
    with open(sparse_checkout_path, "w", encoding="utf-8") as file_handle:
        file_handle.write("options.conf\n")


def determine_default_branch(repo_dir: str) -> str:
    """
    Determine the default branch of the remote repository.

    Args:
        repo_dir: Local directory for the repository

    Returns:
        Name of the default branch (defaults to "master" if not found)
    """
    # Query the remote to get branch information
    ls_remote_process = run_command(
        ["git", "ls-remote", "--symref", "origin", "HEAD"],
        repo_dir,
        text=True,
    )

    # Default to "master" if we can't determine the default branch
    default_branch = "master"

    # Parse the output to find the HEAD symbolic reference
    for line in ls_remote_process.stdout.splitlines():
        if "ref:" in line and "HEAD" in line:
            ref_part = line.split("\t")[0].strip()
            if "refs/heads/" in ref_part:
                default_branch = ref_part.split("refs/heads/")[1]
                break

    return default_branch


def fetch_and_checkout(repo_dir: str, default_branch: str) -> None:
    """
    Fetch and checkout the specified branch with minimal data transfer.

    Args:
        repo_dir: Local directory for the repository
        default_branch: Branch name to checkout
    """
    # Fetch with minimal depth and filtering to reduce data transfer
    run_command(
        [
            "git",
            "fetch",
            "--depth",
            "1",
            "--filter=blob:none",
            "origin",
            default_branch,
        ],
        repo_dir,
    )

    # Checkout the branch
    run_command(["git", "checkout", default_branch], repo_dir)


def clone_repository(pkg_name: str, output_dir: str) -> bool:
    """
    Clone a repository for a specific package using sparse checkout.
    Only retrieves options.conf file to minimize data transfer.

    Args:
        pkg_name: Package name (used as repository name)
        output_dir: Directory to clone repositories into

    Returns:
        True if clone was successful, False otherwise
    """
    repo_url = f"{GITHUB_ORG_URL}/{pkg_name}"
    repo_dir = os.path.join(output_dir, pkg_name)

    # Skip if the repository directory already exists
    if os.path.exists(repo_dir):
        print(f"Skipping {pkg_name}: directory already exists")
        return False

    try:
        # Create the repository directory
        os.makedirs(repo_dir, exist_ok=True)
        print(f"Cloning {pkg_name} (sparse checkout)...")

        # Set up the repository
        initialize_git_repo(repo_dir, repo_url)
        configure_sparse_checkout(repo_dir)

        # Get default branch and checkout
        default_branch = determine_default_branch(repo_dir)
        print(
            f"Using default branch: {default_branch} for {pkg_name}",
        )

        fetch_and_checkout(repo_dir, default_branch)
        return True

    except subprocess.CalledProcessError as e:
        stderr = (
            e.stderr.decode("utf-8").strip()
            if hasattr(e.stderr, "decode")
            else str(e.stderr)
        )
        print(f"Failed to clone {pkg_name}: {stderr}", file=sys.stderr)
        print(
            f"Try checking your network connection or if the repository exists at {repo_url}",
            file=sys.stderr,
        )
        return False
    except OSError as e:
        print(f"OS error when cloning {pkg_name}: {e}", file=sys.stderr)
        print(
            f"Check if you have write permissions to {repo_dir}",
            file=sys.stderr,
        )
        return False


def clone_repositories(
    pkg_names: List[str], output_dir: str, max_workers: int
) -> Dict[str, bool]:
    """
    Clone multiple repositories in parallel with proper interrupt handling.

    Args:
        pkg_names: List of package names to clone
        output_dir: Directory to clone repositories into
        max_workers: Maximum number of parallel workers

    Returns:
        Dictionary mapping package names to clone success status
    """
    global executor, futures_to_cancel
    results = {}

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create the thread pool
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures_map = {}

    try:
        # Submit all cloning tasks to the executor
        for pkg_name in pkg_names:
            future = executor.submit(clone_repository, pkg_name, output_dir)
            futures_map[future] = pkg_name
            futures_to_cancel.add(future)

        # Process the results as they complete
        for future, pkg_name in futures_map.items():
            try:
                results[pkg_name] = future.result()
            except (subprocess.SubprocessError, OSError) as e:
                print(f"Error when cloning {pkg_name}: {e}", file=sys.stderr)
                results[pkg_name] = False
            finally:
                # Remove processed futures from the cancellation set
                if future in futures_to_cancel:
                    futures_to_cancel.remove(future)
    finally:
        # Clean shutdown of the executor
        try:
            if sys.version_info >= (3, 9):
                executor.shutdown(wait=True, cancel_futures=True)
            else:
                # For Python 3.8 and earlier, manually cancel futures
                for future in futures_to_cancel:
                    future.cancel()
                executor.shutdown(wait=True)
        finally:
            # Reset global state
            executor = None
            futures_to_cancel.clear()

    return results


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
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

    return parser.parse_args()


def filter_packages(
    mapping_data: Dict[str, Any], filter_substring: Optional[str] = None
) -> List[str]:
    """
    Filter packages based on mapping data and optional substring filter.

    Args:
        mapping_data: Package mapping data dictionary
        filter_substring: Optional substring to filter package names

    Returns:
        List of filtered package names
    """
    # Get packages with Gentoo mappings
    pkg_names = [
        name
        for name, mapping in mapping_data.items()
        if mapping.get("gentoo_match")
    ]
    print(
        f"Found {len(pkg_names)} packages with Gentoo mappings",
    )

    # Apply additional substring filter if provided
    if filter_substring:
        pkg_names = [name for name in pkg_names if filter_substring in name]
        print(
            f"Filtered to {len(pkg_names)} packages containing '{filter_substring}'"
        )

    # Sort alphabetically for consistent output
    pkg_names.sort()
    return pkg_names


def main():
    """
    Main entry point for the repository cloning script.
    """
    # Set up signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse command-line arguments
    args = parse_arguments()

    # Load package mapping data
    mapping_data = load_mapping_data(args.mapping_file)

    # Filter packages based on criteria
    pkg_names = filter_packages(mapping_data, args.filter)

    # Handle dry-run mode
    if args.dry_run:
        print(f"Would clone {len(pkg_names)} repositories:")
        for pkg_name in pkg_names:
            print(f"  {pkg_name}")
        return

    # Clone repositories
    print(f"Cloning {len(pkg_names)} repositories to {args.output_dir}...")
    results = clone_repositories(pkg_names, args.output_dir, args.max_workers)

    # Print summary
    success_count = sum(1 for success in results.values() if success)
    print(
        f"\nSummary: Successfully cloned {success_count} out of {len(pkg_names)} repositories"
    )

    # Report failures if any
    failed = [pkg_name for pkg_name, success in results.items() if not success]
    if failed:
        print(
            f"\nFailed to clone {len(failed)} repositories:", file=sys.stderr
        )
        for pkg_name in failed:
            print(f"  {pkg_name}", file=sys.stderr)


if __name__ == "__main__":
    main()

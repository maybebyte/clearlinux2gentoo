#!/usr/bin/env python3
"""
Fetch and save package names from Clear Linux GitHub repositories.

This script retrieves a list of non-archived package repositories from
the Clear Linux GitHub organization and saves them to a text file.
"""

# Standard library imports
import argparse
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Mapping, Tuple

# Third-party imports
import requests

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_OUTPUT_FILE = os.path.join(DATA_DIR, "clearlinux_pkgs.txt")
API_BASE_URL = "https://api.github.com/orgs/clearlinux-pkgs/repos"


def fetch_repositories_page(
    page: int, per_page: int = 100
) -> Tuple[List[dict], Mapping[str, str]]:
    """Fetch a single page of repositories from the GitHub API.

    Args:
        page: The page number to fetch
        per_page: Number of items per page

    Returns:
        A tuple containing the list of repositories and the response headers

    Raises:
        requests.RequestException: If the HTTP request fails
    """
    url = f"{API_BASE_URL}?per_page={per_page}&page={page}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), response.headers
    except requests.RequestException as e:
        print(f"Error fetching page {page}: {e}", file=sys.stderr)
        return [], {}


def handle_rate_limiting(headers: Mapping[str, str]) -> bool:
    """Handle GitHub API rate limiting by waiting if necessary.

    Args:
        headers: Response headers from GitHub API

    Returns:
        True if rate limited and waiting, False otherwise
    """
    remaining = int(headers.get("X-RateLimit-Remaining", 0))
    reset_time = int(headers.get("X-RateLimit-Reset", 0))

    print(f"API calls remaining: {remaining}")

    if remaining == 0:
        wait_time = max(reset_time - time.time(), 0) + 5
        reset_datetime = datetime.fromtimestamp(reset_time)
        print(
            f"Rate limit exceeded. Waiting until {reset_datetime.strftime('%H:%M:%S')} "
            f"({int(wait_time / 60)} min {int(wait_time % 60)} sec)",
            file=sys.stderr,
        )
        time.sleep(wait_time)
        return True

    # Add a small delay to be nice to the API
    if remaining > 10:
        time.sleep(0.5)

    return False


def extract_package_names(repositories: List[Dict]) -> List[str]:
    """Extract non-archived package names from repository data.

    Args:
        repositories: List of repository data dictionaries

    Returns:
        List of package names
    """
    return [
        repo["name"]
        for repo in repositories
        if not repo.get("archived", False)
    ]


def get_clearlinux_packages() -> List[str]:
    """Retrieve all non-archived Clear Linux packages from GitHub.

    Returns:
        List of package names
    """
    packages = []
    page = 1
    per_page = 100

    print(
        f"Starting to fetch Clear Linux packages at {datetime.now().strftime('%H:%M:%S')}"
    )

    while True:
        repos, headers = fetch_repositories_page(page, per_page)

        # Check if we're rate limited
        if handle_rate_limiting(headers):
            continue

        # Check if we've reached the end
        if not repos:
            print("No more repositories found")
            break

        # Extract package names and add to our list
        new_packages = extract_package_names(repos)
        packages.extend(new_packages)

        print(
            f"Page {page}: Found {len(new_packages)} packages, total: {len(packages)}"
        )
        page += 1

    print(f"Completed. Retrieved {len(packages)} packages")
    return packages


def save_packages_to_file(packages: List[str], output_file: str) -> None:
    """Save packages to a text file, one per line.

    Args:
        packages: List of package names
        output_file: Path to the output file
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as text_file:
        for pkg in sorted(packages):
            text_file.write(f"{pkg}\n")
    print(f"Package list saved to {output_file}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Fetch Clear Linux packages")
    parser.add_argument(
        "-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file path"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    packages = get_clearlinux_packages()
    save_packages_to_file(packages, args.output)


if __name__ == "__main__":
    main()

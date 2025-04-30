#!/usr/bin/env python3

import time
import json
import os
from datetime import datetime
import argparse
from typing import List

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_OUTPUT_FILE = os.path.join(DATA_DIR, "clearlinux_pkgs.txt")
JSON_OUTPUT_FILE = os.path.join(DATA_DIR, "clearlinux_packages.json")


def get_clearlinux_packages() -> List[str]:
    packages = []
    page = 1
    per_page = 100

    print(
        f"Starting to fetch Clear Linux packages at {datetime.now().strftime('%H:%M:%S')}"
    )

    while True:
        url = f"https://api.github.com/orgs/clearlinux-pkgs/repos?per_page={per_page}&page={page}"
        response = requests.get(url, timeout=10)

        # Check for rate limiting
        remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))

        print(f"API calls remaining: {remaining}")

        if response.status_code == 403 and remaining == 0:
            wait_time = (
                max(reset_time - time.time(), 0) + 5
            )  # Add 5 seconds buffer
            reset_datetime = datetime.fromtimestamp(reset_time)
            print(
                f"Rate limit exceeded. Waiting until {reset_datetime.strftime('%H:%M:%S')} ({int(wait_time/60)} min {int(wait_time%60)} sec)"
            )
            time.sleep(wait_time)
            continue

        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            break

        repos = response.json()
        if not repos:
            print("No more repositories found")
            break

        new_packages = [
            repo["name"] for repo in repos if not repo.get("archived", False)
        ]
        packages.extend(new_packages)

        print(
            f"Page {page}: Found {len(new_packages)} packages, total: {len(packages)}"
        )

        page += 1

        if remaining > 10:
            time.sleep(0.5)

    # Save to file for future use
    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(packages, f, indent=2)

    print(
        f"Completed. Retrieved {len(packages)} packages, saved to {JSON_OUTPUT_FILE}"
    )
    return packages


def save_packages_to_file(packages: List[str], output_file: str) -> None:
    """Save packages to a text file, one per line."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for pkg in sorted(packages):
            f.write(f"{pkg}\n")
    print(f"Package list saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Clear Linux packages")
    parser.add_argument(
        "-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file path"
    )
    args = parser.parse_args()

    packages = get_clearlinux_packages()
    save_packages_to_file(packages, args.output)


if __name__ == "__main__":
    main()

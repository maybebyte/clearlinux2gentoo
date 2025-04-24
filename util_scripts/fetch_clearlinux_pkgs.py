import time
import json
from datetime import datetime
import requests


def get_clearlinux_packages():
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

        new_packages = [repo["name"] for repo in repos]
        packages.extend(new_packages)

        print(
            f"Page {page}: Found {len(new_packages)} packages, total: {len(packages)}"
        )

        page += 1

        if remaining > 10:
            time.sleep(0.5)

    # Save to file for future use
    with open("data/clearlinux_packages.json", "w", encoding="utf-8") as f:
        json.dump(packages, f, indent=2)

    print(
        f"Completed. Retrieved {len(packages)} packages, saved to data/clearlinux_packages.json"
    )
    return packages


if __name__ == "__main__":
    pkgs = get_clearlinux_packages()
    print(pkgs)

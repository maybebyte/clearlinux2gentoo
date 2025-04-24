"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json
import os
import concurrent.futures


def process_chunk(data):
    """
    Process a chunk of Clear Linux packages and find matching Gentoo packages.

    Args:
        data: Tuple containing (clear_linux_packages, gentoo_by_category, all_gentoo_packages)

    Returns:
        Dictionary mapping Clear Linux packages to their Gentoo counterparts
    """
    clear_linux_packages, gentoo_by_category, all_gentoo_packages = data
    results = {}

    # Define category priorities - lower number means higher priority
    priority_categories = {
        # System and core components (highest priority)
        "sys-apps": 10,
        "sys-libs": 10,
        "sys-devel": 10,
        "sys-fs": 10,
        "sys-block": 10,
        "sys-auth": 10,
        "sys-power": 10,
        "sys-process": 10,
        "sys-kernel": 10,
        "sys-boot": 10,
        "sys-firmware": 10,
        "sys-cluster": 10,
        "sys-fabric": 10,
        # Main application categories
        "app-admin": 15,
        "app-arch": 15,
        "app-crypt": 15,
        "app-editors": 15,
        "app-misc": 15,
        "app-shells": 15,
        "app-text": 15,
        "app-containers": 15,
        # Core implementations
        "dev-db": 15,
        "dev-qt": 15,
        "llvm-core": 15,
        "llvm-runtimes": 15,
        "net-misc": 15,
        "net-fs": 15,
        "net-dns": 15,
        "net-firewall": 15,
        "net-wireless": 15,
        "net-vpn": 15,
        "media-sound": 15,
        "media-video": 15,
        "media-libs": 15,
        # Standard libraries and tools
        "dev-libs": 20,
        "dev-util": 20,
        "dev-vcs": 20,
        "dev-lang": 20,
        "dev-build": 20,
        "dev-debug": 20,
        "dev-embedded": 20,
        "dev-tex": 20,
        "dev-texlive": 20,
        "x11-libs": 20,
        "gui-libs": 20,
        "net-libs": 20,
        # Various applications with medium priority
        "app-backup": 25,
        "app-benchmarks": 25,
        "app-office": 25,
        "app-emulation": 25,
        "app-portage": 25,
        "app-alternatives": 25,
        "app-eselect": 25,
        "net-analyzer": 25,
        "net-mail": 25,
        "net-im": 25,
        "net-p2p": 25,
        "net-dialup": 25,
        "net-ftp": 25,
        "net-irc": 25,
        "net-nds": 25,
        "net-news": 25,
        "net-nntp": 25,
        "net-print": 25,
        "net-proxy": 25,
        "net-voip": 25,
        "net-client": 25,
        "www-servers": 25,
        "www-client": 25,
        "www-apache": 25,
        "www-apps": 25,
        "www-misc": 25,
        "x11-terms": 25,
        "x11-wm": 25,
        "x11-drivers": 25,
        "x11-misc": 25,
        # Secondary application categories
        "app-accessibility": 30,
        "app-antivirus": 30,
        "app-cdr": 30,
        "app-dicts": 30,
        "app-doc": 30,
        "app-forensics": 30,
        "app-i18n": 30,
        "app-laptop": 30,
        "app-metrics": 30,
        "app-mobilephone": 30,
        "app-pda": 30,
        "app-officeext": 30,
        "app-voices": 30,
        "mail-client": 30,
        "mail-filter": 30,
        "mail-mta": 30,
        "acct-group": 30,
        "acct-user": 30,
        "media-fonts": 30,
        "media-gfx": 30,
        "media-radio": 30,
        "media-tv": 30,
        "sci-misc": 30,
        "sci-ml": 30,
        "sec-keys": 30,
        "sec-policy": 30,
        "virtual": 30,
        # Desktop environments & related
        "gnome-base": 35,
        "kde-plasma": 35,
        "kde-frameworks": 35,
        "kde-apps": 35,
        "lxde-base": 35,
        "lxqt-base": 35,
        "mate-base": 35,
        "xfce-base": 35,
        "gui-wm": 35,
        "gui-apps": 35,
        "x11-apps": 35,
        "x11-base": 35,
        "phosh-base": 35,
        # Games categories
        "games-action": 40,
        "games-arcade": 40,
        "games-board": 40,
        "games-engines": 40,
        "games-fps": 40,
        "games-puzzle": 40,
        "games-rpg": 40,
        "games-simulation": 40,
        "games-strategy": 40,
        "games-util": 40,
        "games-emulation": 40,
        "games-kids": 40,
        "games-misc": 40,
        "games-mud": 40,
        "games-roguelike": 40,
        "games-server": 40,
        "games-sports": 40,
        # Scientific categories
        "sci-astronomy": 40,
        "sci-biology": 40,
        "sci-calculators": 40,
        "sci-chemistry": 40,
        "sci-electronics": 40,
        "sci-geosciences": 40,
        "sci-libs": 40,
        "sci-mathematics": 40,
        "sci-physics": 40,
        "sci-visualization": 40,
        # Language bindings (lower priority)
        "dev-python": 50,
        "dev-java": 51,
        "dev-cpp": 52,
        "dev-php": 53,
        "dev-go": 54,
        "dev-ruby": 55,
        "dev-perl": 56,
        "dev-lua": 57,
        "dev-dotnet": 58,
        "dev-lisp": 59,
        "dev-elixir": 60,
        "dev-erlang": 61,
        "dev-haskell": 62,
        "dev-tcltk": 63,
        "dev-ml": 64,
        "dev-scheme": 65,
        "dev-nim": 66,
        "dev-zig": 67,
        "dev-crystal": 68,
        "dev-hare": 69,
        "dev-ada": 70,
        "dev-gap": 71,
        "dev-games": 72,
        "perl-core": 73,
        # Extra/plugins categories (lowest priority)
        "app-vim": 80,
        "app-emacs": 80,
        "app-xemacs": 80,
        "kde-misc": 80,
        "gnome-extra": 80,
        "mate-extra": 80,
        "xfce-extra": 80,
        "media-plugins": 80,
        "www-plugins": 80,
        "x11-plugins": 80,
        "x11-themes": 80,
        "mpv-plugin": 80,
        "gnustep-apps": 80,
        "gnustep-base": 80,
        "gnustep-libs": 80,
    }

    default_priority = 30  # Default priority for unlisted categories

    # Process each Clear Linux package
    for package_name in clear_linux_packages:
        # Initialize with no match
        match_result = {
            "gentoo_match": None,
            "confidence": 0,
            "verified": False,
            "all_matches": [],  # Store all possible matches
        }

        # Only look for exact name matches - no normalization
        if package_name in all_gentoo_packages:
            # Find all categories where this package exists
            matching_categories = []
            for category, packages in gentoo_by_category.items():
                if package_name in packages:
                    matching_categories.append(category)
                    match_result["all_matches"].append(
                        f"{category}/{package_name}"
                    )

            if matching_categories:
                # Sort categories by priority and select the best match
                best_category = sorted(
                    matching_categories,
                    key=lambda c: priority_categories.get(c, default_priority),
                )[0]
                match_result = {
                    "gentoo_match": f"{best_category}/{package_name}",
                    "confidence": (
                        1.0 if len(matching_categories) == 1 else 0.8
                    ),
                    "verified": True,
                    "all_matches": match_result["all_matches"],
                }

        results[package_name] = match_result

    return results


def main():
    print("Loading package data...")

    # Load the package lists
    with open("data/gentoo_packages.json", "r", encoding="utf-8") as f:
        gentoo_packages = json.load(f)

    with open("data/clearlinux_packages.json", "r", encoding="utf-8") as f:
        clear_linux_packages = json.load(f)

    print(
        f"Loaded {len(clear_linux_packages)} Clear Linux packages and Gentoo packages from {len(gentoo_packages)} categories"
    )

    # Organize Gentoo packages for efficient lookup
    gentoo_by_category = {}
    all_gentoo_packages = set()

    # Build lookup structures
    for category, packages in gentoo_packages.items():
        gentoo_by_category[category] = set(packages)
        all_gentoo_packages.update(packages)

    print(f"Found {len(all_gentoo_packages)} unique Gentoo package names")

    # Prepare for parallel processing
    cpu_count = os.cpu_count()
    cpu_cores = max(1, int((cpu_count or 1) * 0.75))
    chunk_size = len(clear_linux_packages) // cpu_cores + 1

    # Split the work into chunks
    chunks = []
    for i in range(0, len(clear_linux_packages), chunk_size):
        chunk = clear_linux_packages[i : i + chunk_size]
        chunks.append((chunk, gentoo_by_category, all_gentoo_packages))

    print(f"Processing in {len(chunks)} chunks using {cpu_cores} cores...")

    # Process chunks in parallel
    mapping_results = {}
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=cpu_cores
    ) as executor:
        # Submit all tasks
        future_to_chunk = {
            executor.submit(process_chunk, chunk): i
            for i, chunk in enumerate(chunks)
        }

        # Process as they complete
        print(f"Processing {len(chunks)} chunks...")
        completed = 0
        total = len(chunks)

        for future in concurrent.futures.as_completed(future_to_chunk):
            result = future.result()
            mapping_results.update(result)

            # Update progress
            completed += 1
            percent = (completed / total) * 100
            print(
                f"\rProgress: {completed}/{total} chunks ({percent:.1f}%)",
                end="",
            )

        print()

    # Save the results
    output_file = "data/package_mapping_exact.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)

    # Count matches for the summary
    exact_matches = sum(
        1 for v in mapping_results.values() if v["gentoo_match"]
    )

    print()
    print("Results:")
    print(
        f"- Found {exact_matches} exact matches out of {len(clear_linux_packages)} Clear Linux packages"
    )
    print(f"- Mapping saved to {output_file}")


if __name__ == "__main__":
    main()

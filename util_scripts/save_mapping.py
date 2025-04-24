"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json
import os
import concurrent.futures

# fmt: off
# Define category priorities - lower number means higher priority
PRIORITY_CATEGORIES = {
    # Core system packages - highest priority (lowest numbers)
    "sys-libs": 1,
    "sys-devel": 2,
    "sys-apps": 3,
    "sys-fs": 4,
    "sys-auth": 5,
    "sys-process": 6,
    "sys-cluster": 7,
    "sys-power": 8,
    "sys-block": 9,
    "sys-boot": 10,
    "sys-kernel": 11,
    "sys-firmware": 12,
    "sys-fabric": 13,

    # Basic libraries and development tools
    "dev-libs": 14,
    "dev-build": 15,
    "dev-util": 16,
    "dev-lang": 17,
    "dev-vcs": 18,
    "dev-cpp": 19,
    "dev-db": 20,
    "dev-debug": 21,
    "net-libs": 22,
    "media-libs": 23,
    "sci-libs": 24,
    "x11-libs": 25,
    "gui-libs": 26,
    "llvm-core": 27,
    "llvm-runtimes": 28,

    # Network services and infrastructure
    "net-misc": 29,
    "net-dns": 30,
    "mail-mta": 31,
    "net-mail": 32,
    "www-servers": 33,
    "net-fs": 34,
    "net-proxy": 35,
    "net-analyzer": 36,
    "net-vpn": 37,
    "net-firewall": 38,
    "net-wireless": 39,

    # General applications
    "app-arch": 40,
    "app-crypt": 41,
    "app-containers": 42,
    "app-emulation": 43,
    "app-alternatives": 44,
    "app-admin": 45,
    "app-misc": 46,
    "app-metrics": 47,
    "app-text": 48,
    "app-shells": 49,
    "app-office": 50,
    "app-antivirus": 51,
    "app-portage": 52,
    "app-editors": 53,

    # Desktop environments and GUI
    "gnome-base": 54,
    "kde-plasma": 55,
    "xfce-base": 56,
    "mate-base": 57,
    "lxde-base": 58,
    "lxqt-base": 59,
    "phosh-base": 60,
    "x11-base": 61,
    "x11-wm": 62,
    "gui-wm": 63,
    "x11-terms": 64,
    "x11-apps": 65,

    # Media handling
    "media-video": 66,
    "media-sound": 67,
    "media-gfx": 68,
    "media-radio": 69,
    "media-tv": 70,
    "media-plugins": 71,
    "mpv-plugin": 72,
    "media-fonts": 73,

    # Network applications
    "net-p2p": 74,
    "net-im": 75,
    "net-irc": 76,
    "www-apps": 77,
    "www-client": 78,
    "mail-client": 79,
    "mail-filter": 80,
    "net-news": 81,
    "net-nntp": 82,
    "net-ftp": 83,
    "net-voip": 84,
    "net-print": 85,
    "net-dialup": 86,
    "net-client": 87,
    "net-nds": 88,
    "www-misc": 89,
    "www-apache": 90,
    "www-plugins": 91,

    # Scientific and specialty
    "sci-mathematics": 92,
    "sci-physics": 93,
    "sci-chemistry": 94,
    "sci-biology": 95,
    "sci-electronics": 96,
    "sci-geosciences": 97,
    "sci-visualization": 98,
    "sci-astronomy": 99,
    "sci-calculators": 100,
    "sci-misc": 101,
    "sci-ml": 102,

    # Games
    "games-emulation": 103,
    "games-engines": 104,
    "games-simulation": 105,
    "games-strategy": 106,
    "games-rpg": 107,
    "games-action": 108,
    "games-fps": 109,
    "games-arcade": 110,
    "games-puzzle": 111,
    "games-board": 112,
    "games-sports": 113,
    "games-util": 114,
    "games-roguelike": 115,
    "games-misc": 116,
    "games-kids": 117,
    "games-mud": 118,
    "games-server": 119,

    # Desktop extras and theming
    "gnome-extra": 120,
    "kde-apps": 121,
    "kde-frameworks": 122,
    "kde-misc": 123,
    "xfce-extra": 124,
    "mate-extra": 125,
    "x11-misc": 126,
    "gui-apps": 127,
    "x11-themes": 128,
    "x11-plugins": 129,
    "x11-drivers": 130,

    # Specialty applications
    "app-backup": 131,
    "app-benchmarks": 132,
    "app-cdr": 133,
    "app-dicts": 134,
    "app-doc": 135,
    "app-accessibility": 136,
    "app-forensics": 137,
    "app-i18n": 138,
    "app-laptop": 139,
    "app-mobilephone": 140,
    "app-officeext": 141,
    "app-pda": 142,
    "app-vim": 143,
    "app-emacs": 144,
    "app-eselect": 145,
    "app-voices": 146,
    "app-xemacs": 147,

    # More specialized development frameworks
    "dev-embedded": 148,
    "dev-ml": 149,
    "dev-games": 150,
    "dev-qt": 151,
    "dev-tcltk": 152,
    "dev-tex": 153,
    "dev-texlive": 154,
    "dev-ada": 155,
    "dev-dotnet": 156,
    "dev-gap": 157,
    "dev-hare": 158,
    "dev-lisp": 159,
    "dev-nim": 160,
    "dev-scheme": 161,
    "dev-zig": 162,
    "dev-go": 163,
    "dev-elixir": 164,
    "gnustep-base": 165,
    "gnustep-libs": 166,
    "gnustep-apps": 167,

    # Language bindings (often wrappers)
    "dev-python": 168,
    "dev-ruby": 169,
    "dev-perl": 170,
    "dev-php": 171,
    "dev-lua": 172,
    "dev-java": 173,
    "dev-haskell": 174,
    "dev-erlang": 175,
    "dev-crystal": 176,
    "perl-core": 177,

    # Virtual/abstract packages
    "virtual": 178,

    # Security
    "sec-keys": 179,
    "sec-policy": 180,

    # Account groups and users - lowest priority (highest numbers)
    "acct-user": 181,
    "acct-group": 182,
}
# fmt: on

# Manual overrides for package mappings that would otherwise be incorrect
MANUAL_PACKAGE_OVERRIDES = {
    "SDL": "media-libs/libsdl",
    "fmt": "dev-libs/libfmt",
    "httpd": "www-servers/apache",
}

DEFAULT_PRIORITY = 30  # Default priority for unlisted categories


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

    # Process each Clear Linux package
    for package_name in clear_linux_packages:
        # Initialize with no match
        match_result = {
            "gentoo_match": None,
            "confidence": 0,
            "verified": False,
            "all_matches": [],  # Store all possible matches
        }

        # Check for manual override first
        if package_name in MANUAL_PACKAGE_OVERRIDES:
            match_result = {
                "gentoo_match": MANUAL_PACKAGE_OVERRIDES[package_name],
                "confidence": 1.0,  # Override means high confidence
                "verified": True,
                "all_matches": [MANUAL_PACKAGE_OVERRIDES[package_name]],
            }
            results[package_name] = match_result
            continue

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
                    key=lambda c: PRIORITY_CATEGORIES.get(c, DEFAULT_PRIORITY),
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

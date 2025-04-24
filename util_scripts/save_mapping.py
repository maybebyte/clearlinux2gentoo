"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json
import os
import concurrent.futures


# Categories that don't benefit from compile-time optimizations
NON_OPTIMIZABLE_CATEGORIES = {
    "acct-group",
    "acct-user",
    "app-alternatives",
    "app-dicts",
    "app-doc",
    "app-emacs",
    "app-vim",
    "app-voices",
    "app-xemacs",
    "media-fonts",
    "sec-keys",
    "virtual",
    "x11-themes",
}

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
                # Skip categories that don't benefit from optimization
                if category in NON_OPTIMIZABLE_CATEGORIES:
                    continue

                if package_name in packages:
                    matching_categories.append(category)
                    match_result["all_matches"].append(
                        f"{category}/{package_name}"
                    )

            if matching_categories:
                # Simply use the first category alphabetically as the best match
                # XXX: not permanent! Just a temporary kludge for testing
                best_category = sorted(matching_categories)[0]
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

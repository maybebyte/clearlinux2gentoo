"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using case-insensitive name matching
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


def get_manual_override_match(package_name, overrides=None):
    """
    Check if a package has a manual override and return the match result if it does.

    Args:
        package_name: The package name to check
        overrides: Dictionary of manual overrides (defaults to MANUAL_PACKAGE_OVERRIDES)

    Returns:
        Match result dictionary if override exists, None otherwise
    """
    if overrides is None:
        overrides = MANUAL_PACKAGE_OVERRIDES

    if package_name in overrides:
        return {
            "gentoo_match": overrides[package_name],
            "confidence": 1.0,
            "verified": True,
            "all_matches": [overrides[package_name]],
        }
    return None


def process_chunk(data):
    """
    Process a chunk of Clear Linux packages and find matching Gentoo packages.

    Args:
        data: Tuple containing (clear_linux_packages, gentoo_by_category, all_gentoo_packages, case_mapping)

    Returns:
        Dictionary mapping Clear Linux packages to their Gentoo counterparts
    """
    clear_linux_packages, gentoo_by_category, all_gentoo_packages, case_mapping = data
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
        override_match = get_manual_override_match(package_name)
        if override_match:
            results[package_name] = override_match
            continue

        # Case-insensitive lookup
        package_name_lower = package_name.lower()
        if package_name_lower in all_gentoo_packages:
            # Find all categories where this package exists
            matching_categories = []
            for category, packages in gentoo_by_category.items():
                # Skip categories that don't benefit from optimization
                if category in NON_OPTIMIZABLE_CATEGORIES:
                    continue

                if package_name_lower in packages:
                    matching_categories.append(category)
                    # Use original case from Gentoo packages
                    original_case = case_mapping.get((category, package_name_lower), package_name)
                    match_result["all_matches"].append(
                        f"{category}/{original_case}"
                    )

            if matching_categories:
                # Simply use the first category alphabetically as the best match
                # XXX: not permanent! Just a temporary kludge for testing
                best_category = sorted(matching_categories)[0]
                # Get original case
                original_case = case_mapping.get((best_category, package_name_lower), package_name)
                match_result = {
                    "gentoo_match": f"{best_category}/{original_case}",
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
    case_mapping = {}  # Track original case of package names

    # Build lookup structures
    for category, packages in gentoo_packages.items():
        # Store lowercase versions for case-insensitive comparison
        gentoo_by_category[category] = set(pkg.lower() for pkg in packages)

        # Map lowercase names to original case
        for pkg in packages:
            pkg_lower = pkg.lower()
            all_gentoo_packages.add(pkg_lower)
            case_mapping[(category, pkg_lower)] = pkg

    print(f"Found {len(all_gentoo_packages)} unique Gentoo package names")

    # Prepare for parallel processing
    cpu_count = os.cpu_count()
    cpu_cores = max(1, int((cpu_count or 1) * 0.75))
    chunk_size = len(clear_linux_packages) // cpu_cores + 1

    # Split the work into chunks
    chunks = []
    for i in range(0, len(clear_linux_packages), chunk_size):
        chunk = clear_linux_packages[i : i + chunk_size]
        chunks.append((chunk, gentoo_by_category, all_gentoo_packages, case_mapping))

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
    output_file = "data/package_mapping_case_insensitive.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)

    # Count matches for the summary
    matches = sum(
        1 for v in mapping_results.values() if v["gentoo_match"]
    )

    print()
    print("Results:")
    print(
        f"- Found {matches} matches out of {len(clear_linux_packages)} Clear Linux packages"
    )
    print(f"- Mapping saved to {output_file}")


if __name__ == "__main__":
    main()

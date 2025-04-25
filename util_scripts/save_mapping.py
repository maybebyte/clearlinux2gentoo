"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json

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


def get_manual_override_for_package(package_name: str) -> dict | None:
    """
    Determines if a package has a manual override. Returns the match details.

    Args:
        package_name (str): The name of the package to check.

    Returns:
        dict | None: Either a dict with match details if an override exists,
                     or None if no override is found.
    """
    overrides = MANUAL_PACKAGE_OVERRIDES

    if package_name in overrides:
        return {
            "gentoo_match": overrides[package_name],
            "confidence": 1.0,
            "verified": True,
            "all_matches": [overrides[package_name]],
        }
    return None


def main():
    # Load the package lists
    with open("data/gentoo_packages.json", "r", encoding="utf-8") as f:
        gentoo_packages = json.load(f)

    with open("data/clearlinux_packages.json", "r", encoding="utf-8") as f:
        clear_linux_packages = json.load(f)

    # Organize Gentoo packages for efficient lookup
    gentoo_by_category = {}
    all_gentoo_packages = set()

    # Build lookup structures - using exact names
    for category, packages in gentoo_packages.items():
        gentoo_by_category[category] = set(packages)
        all_gentoo_packages.update(packages)

    # Process all packages sequentially
    mapping_results = {}

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
        override_match = get_manual_override_for_package(package_name)
        if override_match:
            mapping_results[package_name] = override_match
            continue

        # Exact matching lookup
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

        mapping_results[package_name] = match_result

    # Save the results
    output_file = "data/package_mapping_exact.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

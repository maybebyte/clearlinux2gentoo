"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json
from collections import defaultdict

CLEARLINUX_PKG_FILE = "data/clearlinux_pkgs.txt"
GENTOO_PKG_FILE = "data/gentoo_pkgs.txt"

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


def gentoo_pkgfile_to_dict(file_path: str) -> dict:
    """
    Loads Gentoo packages from a file and organizes them by category.

    Args:
        file_path (str): Path to the Gentoo package file.

    Returns:
        dict: A dictionary mapping categories to sets of package names.
    """
    gentoo_category_to_pkgs = defaultdict(set)
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            category, pkgs = line.split("/", 1)
            gentoo_category_to_pkgs[category].add(pkgs)
    return gentoo_category_to_pkgs


def extract_pkgs_from_dict(category_to_pkgs: dict) -> set:
    """
    Extracts all unique package names from a dictionary mapping categories
    to package sets.

    Args:
        category_to_pkgs (dict): A dictionary where keys are categories and
            values are sets of package names.

    Returns:
        set: A set of all unique package names.
    """
    all_packages = set()
    for pkgs in category_to_pkgs.values():
        all_packages.update(pkgs)
    return all_packages


def main():
    gentoo_category_to_pkgs = gentoo_pkgfile_to_dict(GENTOO_PKG_FILE)
    all_gentoo_pkgs = extract_pkgs_from_dict(gentoo_category_to_pkgs)

    with open(CLEARLINUX_PKG_FILE, "r", encoding="utf-8") as f:
        clearlinux_pkgs = {line.strip() for line in f}

    mapping_results = {}

    for pkg_name in clearlinux_pkgs:
        match_result = {
            "gentoo_match": None,
            "confidence": 0,
            "verified": False,
            "all_matches": [],
        }

        override_match = get_manual_override_for_package(pkg_name)
        if override_match:
            mapping_results[pkg_name] = override_match
            continue

        if pkg_name in all_gentoo_pkgs:
            matching_categories = []
            for category, pkgs in gentoo_category_to_pkgs.items():
                if category in NON_OPTIMIZABLE_CATEGORIES:
                    continue

                if pkg_name in pkgs:
                    matching_categories.append(category)
                    match_result["all_matches"].append(
                        f"{category}/{pkg_name}"
                    )

            if matching_categories:
                # Simply use the first category alphabetically as the best match
                # XXX: not permanent! Just a temporary kludge for testing
                best_category = sorted(matching_categories)[0]
                match_result = {
                    "gentoo_match": f"{best_category}/{pkg_name}",
                    "confidence": (
                        1.0 if len(matching_categories) == 1 else 0.8
                    ),
                    "verified": True,
                    "all_matches": match_result["all_matches"],
                }

        mapping_results[pkg_name] = match_result

    output_file = "data/package_mapping_exact.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

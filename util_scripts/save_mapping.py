"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using exact name matching
"""

import json
from collections import defaultdict

CLEARLINUX_PKG_FILE = "data/clearlinux_pkgs.txt"
GENTOO_PKG_FILE = "data/gentoo_pkgs.txt"
OUTPUT_FILE = "data/pkg_mapping.json"

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
MANUAL_PKG_OVERRIDES = {
    "SDL": "media-libs/libsdl",
    "fmt": "dev-libs/libfmt",
    "httpd": "www-servers/apache",
}


def get_manual_override_for_pkg(pkg_name: str) -> dict | None:
    """
    Determines if a package has a manual override. Returns the match details.

    Args:
        package_name (str): The name of the package to check.

    Returns:
        dict | None: Either a dict with match details if an override exists,
                     or None if no override is found.
    """
    overrides = MANUAL_PKG_OVERRIDES

    if pkg_name in overrides:
        return {
            "gentoo_match": overrides[pkg_name],
            "confidence": 1.0,
            "all_matches": [overrides[pkg_name]],
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


def clearlinux_pkgfile_to_set(file_path: str) -> set:
    """
    Loads Clear Linux package names from a file.

    Args:
        file_path (str): Path to the Clear Linux package file.

    Returns:
        set: A set of package names.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f}


def gentoo_dict_to_pkglist(category_to_pkgs: dict) -> set:
    """
    Extracts all unique package names from a dictionary mapping categories
    to package sets.

    Args:
        category_to_pkgs (dict): A dictionary where keys are categories and
            values are sets of package names.

    Returns:
        set: A set of all unique package names.
    """
    all_pkgs = set()
    for pkgs in category_to_pkgs.values():
        all_pkgs.update(pkgs)
    return all_pkgs


def process_pkg_mapping(
    pkg_name: str,
    gentoo_category_to_pkgs: dict,
    all_gentoo_pkgs: set,
) -> dict:
    """
    Processes the mapping for a single package.

    Args:
        pkg_name (str): The package name to process.
        all_gentoo_pkgs (set): Set of all Gentoo package names.
        gentoo_category_to_pkgs (dict): Dictionary mapping Gentoo
            categories to package sets.

    Returns:
        dict: Mapping result for the package.
    """

    def find_matching_categories(pkg_name: str) -> list:
        matching_categories = []
        for category, pkgs in gentoo_category_to_pkgs.items():
            if category not in NON_OPTIMIZABLE_CATEGORIES and pkg_name in pkgs:
                matching_categories.append(category)
        return matching_categories

    # XXX: will fix with a proper category prioritization system later
    def determine_best_pkg_category(categories: list) -> str | None:
        return sorted(categories)[0] if categories else None

    override_match = get_manual_override_for_pkg(pkg_name)
    if override_match:
        return override_match

    match_result = {
        "gentoo_match": None,
        "confidence": 0,
        "all_matches": [],
    }

    if pkg_name in all_gentoo_pkgs:
        matching_categories = find_matching_categories(pkg_name)
        match_result["all_matches"] = [
            f"{category}/{pkg_name}" for category in matching_categories
        ]

        if matching_categories:
            best_category = determine_best_pkg_category(matching_categories)
            confidence = (
                0.8
                if len(matching_categories) == 1
                else round(1 / len(matching_categories), 3)
            )
            match_result.update(
                {
                    "gentoo_match": f"{best_category}/{pkg_name}",
                    "confidence": confidence,
                }
            )

    return match_result


def main():
    gentoo_category_to_pkgs = gentoo_pkgfile_to_dict(GENTOO_PKG_FILE)
    all_gentoo_pkgs = gentoo_dict_to_pkglist(gentoo_category_to_pkgs)
    clearlinux_pkgs = clearlinux_pkgfile_to_set(CLEARLINUX_PKG_FILE)

    mapping_results = {}
    for pkg_name in clearlinux_pkgs:
        match_result = process_pkg_mapping(
            pkg_name, gentoo_category_to_pkgs, all_gentoo_pkgs
        )
        mapping_results[pkg_name] = match_result

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

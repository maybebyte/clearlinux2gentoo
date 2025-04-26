"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using
case-insensitive name matching
"""

import json
from collections import defaultdict
from typing import Dict, List, Optional, Set

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


def find_manual_override(pkg_name: str) -> Optional[Dict]:
    """
    Check if a package has a manual override mapping.

    Args:
        pkg_name: The package name to check.

    Returns:
        A dictionary with match details if an override exists, None otherwise.
    """
    if pkg_name in MANUAL_PKG_OVERRIDES:
        gentoo_pkg_path = MANUAL_PKG_OVERRIDES[pkg_name]
        return {
            "gentoo_match": gentoo_pkg_path,
            "confidence": 1.0,
            "all_matches": [gentoo_pkg_path],
        }
    return None


def load_gentoo_packages(file_path: str) -> Dict[str, Set[str]]:
    """
    Load Gentoo packages from a file, organized by category.

    Args:
        file_path: Path to the Gentoo package file.

    Returns:
        Dictionary mapping categories to sets of package names.
    """
    category_to_pkgs = defaultdict(set)
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            category, pkg_name = line.split("/", 1)
            category_to_pkgs[category].add(pkg_name)
    return category_to_pkgs


def load_clearlinux_packages(file_path: str) -> Set[str]:
    """
    Load Clear Linux package names from a file.

    Args:
        file_path: Path to the Clear Linux package file.

    Returns:
        Set of package names.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f}


class PackageMatcher:
    """Handles case-insensitive package matching between distributions."""

    def __init__(self, category_to_pkgs: Dict[str, Set[str]]):
        """
        Initialize with Gentoo package data and build lookup tables.

        Args:
            category_to_pkgs: Dictionary mapping categories to package sets.
        """
        self.lowercase_to_original: Dict[str, str] = {}
        self.lowercase_pkg_names: Set[str] = set()
        self.pkg_to_eligible_categories: Dict[str, List[str]] = defaultdict(
            list
        )

        self._build_lookup_tables(category_to_pkgs)

    def _build_lookup_tables(self, category_to_pkgs: Dict[str, Set[str]]):
        """
        Build lookup tables for efficient case-insensitive matching.

        Args:
            category_to_pkgs: Dictionary mapping categories to package sets.
        """
        for category, pkgs in category_to_pkgs.items():
            is_optimizable = category not in NON_OPTIMIZABLE_CATEGORIES

            for pkg in pkgs:
                lowercase_pkg = pkg.lower()
                self.lowercase_pkg_names.add(lowercase_pkg)
                self.lowercase_to_original[lowercase_pkg] = pkg

                if is_optimizable:
                    self.pkg_to_eligible_categories[lowercase_pkg].append(
                        category
                    )

    def find_matching_categories(self, pkg_name: str) -> List[str]:
        """
        Find categories where this package exists (case-insensitive).

        Args:
            pkg_name: The package name to search for.

        Returns:
            List of matching category names.
        """
        return self.pkg_to_eligible_categories.get(pkg_name.lower(), [])

    def get_original_case(self, pkg_name: str) -> str:
        """
        Get the original case of a package name.

        Args:
            pkg_name: The package name to look up.

        Returns:
            Original case of the package name, or the input if not found.
        """
        return self.lowercase_to_original.get(pkg_name.lower(), pkg_name)

    def package_exists(self, pkg_name: str) -> bool:
        """
        Check if a package exists (case-insensitive).

        Args:
            pkg_name: The package name to check.

        Returns:
            True if the package exists, False otherwise.
        """
        return pkg_name.lower() in self.lowercase_pkg_names


# XXX: will create a proper implementation later
def select_best_category(categories: List[str]) -> Optional[str]:
    """
    Select the best category for a package from multiple matches.

    Args:
        categories: List of matching categories.

    Returns:
        The best category, or None if no categories are provided.
    """
    return sorted(categories)[0] if categories else None


def calculate_confidence(matching_categories: List[str]) -> float:
    """
    Calculate confidence level based on number of matching categories.

    Args:
        matching_categories: List of matching categories.

    Returns:
        Confidence level (0.0-1.0).
    """
    if not matching_categories:
        return 0.0

    if len(matching_categories) == 1:
        return 0.8

    return round(1 / len(matching_categories), 3)


def create_match_result(
    gentoo_match: Optional[str] = None,
    confidence: float = 0.0,
    all_matches: Optional[List[str]] = None,
) -> Dict:
    """
    Create a standardized match result dictionary.

    Args:
        gentoo_match: Best matching Gentoo package path.
        confidence: Confidence level of the match.
        all_matches: List of all possible matches.

    Returns:
        Match result dictionary.
    """
    return {
        "gentoo_match": gentoo_match,
        "confidence": confidence,
        "all_matches": all_matches or [],
    }


def map_package(pkg_name: str, matcher: PackageMatcher) -> Dict:
    """
    Map a Clear Linux package to its Gentoo equivalent.

    Args:
        pkg_name: Clear Linux package name to map.
        matcher: PackageMatcher with lookup tables.

    Returns:
        Mapping result dictionary.
    """
    override_match = find_manual_override(pkg_name)
    if override_match:
        return override_match

    if not matcher.package_exists(pkg_name):
        return create_match_result()

    matching_categories = matcher.find_matching_categories(pkg_name)
    if not matching_categories:
        return create_match_result()

    original_case_pkg = matcher.get_original_case(pkg_name)

    all_matches = [
        f"{category}/{original_case_pkg}" for category in matching_categories
    ]

    best_category = select_best_category(matching_categories)
    confidence = calculate_confidence(matching_categories)
    best_match = f"{best_category}/{original_case_pkg}"

    return create_match_result(best_match, confidence, all_matches)


def save_mapping_to_json(mapping_results: Dict, output_file: str):
    """
    Save mapping results to a JSON file.

    Args:
        mapping_results: Dictionary of mapping results.
        output_file: Path to output file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping_results, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    gentoo_packages = load_gentoo_packages(GENTOO_PKG_FILE)
    clearlinux_packages = load_clearlinux_packages(CLEARLINUX_PKG_FILE)

    matcher = PackageMatcher(gentoo_packages)

    mapping_results = {}
    for pkg_name in clearlinux_packages:
        mapping_results[pkg_name] = map_package(pkg_name, matcher)

    save_mapping_to_json(mapping_results, OUTPUT_FILE)


if __name__ == "__main__":
    main()

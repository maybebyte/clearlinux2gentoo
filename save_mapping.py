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
    "intel-media-driver": "media-libs/libva-intel-media-driver",
    "intel-hybrid-driver": "media-libs/intel-hybrid-codec-driver",
    "CGNS": "sci-libs/cgnslib",
    "Linux-PAM": "sys-libs/pam",
    "FreeRDP2": "net-misc/freerdp",
    "awesome-wm": "x11-wm/awesome",
    "bind-utils": "net-dns/bind-tools",
    "boinc-client": "net-misc/boinc",
    "ghostscript": "app-text/ghostscript-gpl",
    "gnome-tweak-tool": "gnome-extra/gnome-tweaks",
    "graphite": "dev-libs/graphite2",
    "gtk4": "gui-libs/gtk",
    "gtk3": "x11-libs/gtk+",
    "gtkspell3": "app-text/gtkspell",
    "lcms2": "media-libs/lcms",
    "taskwarrior": "app-misc/task",
    "thermal_daemon": "sys-power/thermald",
    "udisks2": "sys-fs/udisks",
    "v4l-utils": "media-libs/libv4l",
    "webkitgtk": "net-libs/webkit-gtk",
}

PREFIX_MAPPINGS = {
    # without transforms
    "golang-": {"category": "dev-go", "transform": None},
    "jdk-": {"category": "dev-java", "transform": None},
    "mvn-": {"category": "dev-java", "transform": None},
    "perl-": {"category": "dev-perl", "transform": None},
    "php-": {"category": "dev-php", "transform": None},
    "pypi-": {"category": "dev-python", "transform": None},
    "python-": {"category": "dev-python", "transform": None},
    "rubygem-": {"category": "dev-ruby", "transform": None},
    # with transforms
    "qt6": {"category": "dev-qt", "transform": "qt"},
    "zope.": {"category": "dev-python", "transform": "zope-"},
    "pypi-zope.": {"category": "dev-python", "transform": "zope-"},
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
        self.pkg_case_by_category: Dict[str, Dict[str, str]] = defaultdict(
            dict
        )
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
                self.pkg_case_by_category[lowercase_pkg][category] = pkg

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

    def get_case_in_category(
        self, pkg_name: str, category: str
    ) -> Optional[str]:
        """
        Get the exact case of a package as it appears in a specific category.

        Args:
            pkg_name: The package name to look up.
            category: The specific category to check.

        Returns:
            The original case in that category, or None if not found.
        """
        lowercase_pkg = pkg_name.lower()

        if (
            lowercase_pkg in self.pkg_case_by_category
            and category in self.pkg_case_by_category[lowercase_pkg]
        ):
            return self.pkg_case_by_category[lowercase_pkg][category]

        return None

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
def select_best_category(categories: List[str]) -> str:
    """
    Select the best category for a package from multiple matches.

    Args:
        categories: List of matching categories.

    Returns:
        The best category, or None if no categories are provided.
    """
    return sorted(categories)[0] if categories else ""


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


def extract_package_info(pkg_name: str) -> tuple[str, Optional[str]]:
    """
    Extract base package name and required category from prefixed package names

    Args:
        pkg_name: The package name that may contain a prefix.

    Returns:
        A tuple of (transformed_name, required_category) where:
        - transformed_name: The processed package name after prefix/transform
          rules
        - required_category: The mandatory Gentoo category for the package
    """
    for prefix, mapping in PREFIX_MAPPINGS.items():
        if pkg_name.startswith(prefix):
            base_name = pkg_name[len(prefix) :]

            if mapping["transform"]:
                transformed_name = mapping["transform"] + base_name
            else:
                transformed_name = base_name

            return transformed_name, mapping["category"]

    return pkg_name, None


def try_map_package(
    pkg_name: str,
    matcher: PackageMatcher,
    required_category: Optional[str] = None,
) -> Optional[Dict]:
    """
    Helper function to try mapping a package name to Gentoo.

    Args:
        pkg_name: Package name to map.
        matcher: PackageMatcher with lookup tables.
        required_category: If provided, only consider matches in this category.

    Returns:
        Mapping result dictionary or None if no match.
    """
    override_match = find_manual_override(pkg_name)
    if override_match:
        return override_match

    if not matcher.package_exists(pkg_name):
        return None

    matching_categories = matcher.find_matching_categories(pkg_name)
    if not matching_categories:
        return None

    if required_category:
        if required_category not in matching_categories:
            return None
        matching_categories = [required_category]

    all_matches = []
    for category in matching_categories:
        category_specific_case = matcher.get_case_in_category(
            pkg_name, category
        )
        if category_specific_case:
            all_matches.append(f"{category}/{category_specific_case}")

    best_category = select_best_category(matching_categories)
    category_specific_case = matcher.get_case_in_category(
        pkg_name, best_category
    )

    if category_specific_case:
        best_match = f"{best_category}/{category_specific_case}"
        confidence = calculate_confidence(matching_categories)
        return create_match_result(best_match, confidence, all_matches)

    return None


def map_package(pkg_name: str, matcher: PackageMatcher) -> Dict:
    """
    Map a Clear Linux package to its Gentoo equivalent.

    Args:
        pkg_name: Clear Linux package name to map.
        matcher: PackageMatcher with lookup tables.

    Returns:
        Mapping result dictionary.
    """
    result = try_map_package(pkg_name, matcher)
    if result:
        return result

    transformed_name, required_category = extract_package_info(pkg_name)
    if transformed_name != pkg_name:
        result = try_map_package(transformed_name, matcher, required_category)
        if result:
            return result

    return create_match_result()


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

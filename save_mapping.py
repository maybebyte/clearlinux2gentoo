#!/usr/bin/env python3

"""
Package Mapper - Maps Clear Linux packages to Gentoo packages using
case-insensitive name matching
"""

import json
from collections import defaultdict
from typing import Dict, List, Optional, Set
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "data"
CLEARLINUX_PKG_FILE = os.path.join(BASE_DIR, DATA_DIR, "clearlinux_pkgs.txt")
GENTOO_PKG_FILE = os.path.join(BASE_DIR, DATA_DIR, "gentoo_pkgs.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, DATA_DIR, "pkg_mapping.json")

# TODO: resolve bug that causes other packages to be listed, e.g. mvn-xz
# and jdk-xz now get listed if I map xz to xz-utils

# This is for the category prioritization system
DEFAULT_LOWEST_PRIORITY = 999

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
    "boinc-client": "sci-misc/boinc",
    "ghostscript": "app-text/ghostscript-gpl",
    "graphite": "media-gfx/graphite2",
    "gtk4": "gui-libs/gtk",
    "gtk3": "x11-libs/gtk+",
    "gtkspell3": "app-text/gtkspell",
    "lcms2": "media-libs/lcms",
    "taskwarrior": "app-misc/task",
    "thermal_daemon": "sys-power/thermald",
    "udisks2": "sys-fs/udisks",
    "v4l-utils": "media-libs/libv4l",
    "webkitgtk": "net-libs/webkit-gtk",
    "xz": "app-arch/xz-utils",
    "wine": "app-emulation/wine-vanilla",  # TODO: map to wine-staging and wine-proton too
    "ntfs-3g": "sys-fs/ntfs3g",
    "mesa-clc": "dev-util/mesa_clc",
    "mediasdk": "media-libs/intel-mediasdk",
    "intel-gmmlib": "media-libs/gmmlib",
    "icu4c": "dev-libs/icu",
    "WireGuard": "net-vpn/wireguard-tools",
    "procps-ng": "sys-process/procps",
    "utf8proc": "dev-libs/libutf8proc",
    "xapian-core": "dev-libs/xapian",
    "raptor2": "media-libs/raptor",
    "pcre": "dev-libs/libpcre",
    "pcre2": "dev-libs/libpcre2",
    "openal-soft": "media-libs/openal",
    "qcoro6": "dev-libs/qcoro",
    "msgpack-c": "dev-libs/msgpack",
    "librtlsdr": "net-wireless/rtl-sdr",
    "gtk-plus": "x11-libs/gtk+",
    "SDL2": "media-libs/libsdl2",
    "SDL2_gfx": "media-libs/sdl2-gfx",
    "SDL2_image": "media-libs/sdl2-image",
    "SDL2_mixer": "media-libs/sdl2-mixer",
    "SDL2_net": "media-libs/sdl2-net",
    "SDL2_ttf": "media-libs/sdl2-ttf",
    "SDL3": "media-libs/libsdl3",
    "SFML": "media-libs/libsfml",
    "clucene-core": "dev-cpp/clucene",
    "gc": "dev-libs/boehm-gc",
    "gperftools": "dev-util/google-perftools",
    "gtksourceview": "gui-libs/gtksourceview",
    "gtksourceview4": "x11-libs/gtksourceview",
    "hiredis-c": "dev-libs/hiredis",
    "libsigc-plus-plus": "dev-libs/libsigc++",
    "ocl-icd": "dev-libs/opencl-icd-loader",
    "xorgproto": "x11-base/xorg-proto",
    "SDL_gfx": "media-libs/sdl-gfx",
    "SDL_image": "media-libs/sdl-image",
    "SDL_mixer": "media-libs/sdl-mixer",
    "SDL_net": "media-libs/sdl-net",
    "SDL_ttf": "media-libs/sdl-ttf",
    "xvidcore": "media-libs/xvid",
    "arpack-ng": "sci-libs/arpack",
    "libMED": "sci-libs/med",
    "libgd": "media-libs/gd",
    "libzmq": "net-libs/zeromq",
    "onig": "dev-libs/oniguruma",
    "libftdi1": "dev-embedded/libftdi",
    "googletest": "dev-cpp/gtest",
    "google-benchmark": "dev-cpp/benchmark",
    "google-crc32c": "dev-libs/crc32c",
    "not-ffmpeg": "media-video/ffmpeg",
    "gstreamer-vaapi": "media-plugins/gst-plugins-vaapi",
    "xmlsec1": "dev-libs/xmlsec",
    "indi": "sci-libs/indilib",
    "kdeconnect-kde": "kde-misc/kdeconnect",
    "valkey": "dev-db/redis",
    "mc": "app-misc/mc",
    "exo": "xfce-base/exo",
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

# fmt: off
CATEGORY_PRIORITY = {
    # Core system components - highest priority
    "sys-libs": 10,
    "sys-apps": 11,
    "sys-devel": 12,
    "sys-fs": 13,
    "sys-process": 14,
    "sys-kernel": 15,
    "sys-firmware": 16,
    "sys-boot": 17,
    "sys-auth": 18,
    "sys-power": 19,
    "sys-block": 20,
    "sys-cluster": 21,
    "sys-fabric": 22,

    # Primary implementation libraries
    "dev-libs": 30,
    "media-libs": 31,
    "x11-libs": 32,
    "net-libs": 33,
    "sci-libs": 34,
    "gui-libs": 35,
    "llvm-core": 36,
    "llvm-runtimes": 37,

    # Core applications and tools
    "app-arch": 40,
    "app-crypt": 41,
    "app-containers": 42,
    "app-text": 43,
    "app-admin": 44,
    "app-misc": 45,
    "app-editors": 46,
    "app-emulation": 47,
    "dev-vcs": 48,
    "dev-util": 49,
    "dev-build": 50,
    "dev-debug": 51,
    "net-misc": 52,
    "net-fs": 53,
    "net-vpn": 54,
    "net-analyzer": 55,

    # Core generic language implementations
    "dev-lang": 60,

    # Secondary applications
    "app-shells": 70,
    "app-office": 71,
    "app-portage": 72,
    "app-benchmarks": 73,
    "app-backup": 74,
    "app-forensics": 75,
    "app-i18n": 76,
    "www-servers": 77,
    "www-client": 78,
    "net-dns": 79,
    "net-mail": 80,
    "net-firewall": 81,
    "net-ftp": 82,
    "net-im": 83,
    "net-irc": 84,
    "mail-client": 85,
    "mail-filter": 86,
    "mail-mta": 87,

    # Databases and related
    "dev-db": 90,

    # Desktop environments
    "x11-base": 100,
    "x11-apps": 101,
    "x11-wm": 102,
    "x11-terms": 103,
    "x11-drivers": 104,
    "x11-misc": 105,
    "x11-plugins": 106,
    "gnome-base": 107,
    "kde-frameworks": 108,
    "kde-plasma": 109,
    "kde-apps": 110,
    "kde-misc": 111,
    "gui-wm": 112,
    "gui-apps": 113,
    "lxde-base": 114,
    "lxqt-base": 115,
    "xfce-base": 116,
    "xfce-extra": 117,
    "mate-base": 118,
    "mate-extra": 119,
    "gnome-extra": 120,
    "phosh-base": 121,

    # Media applications
    "media-gfx": 130,
    "media-sound": 131,
    "media-video": 132,
    "media-tv": 133,
    "media-plugins": 134,
    "media-radio": 135,
    "mpv-plugin": 136,

    # Science applications
    "sci-mathematics": 140,
    "sci-physics": 141,
    "sci-chemistry": 142,
    "sci-astronomy": 143,
    "sci-biology": 144,
    "sci-electronics": 145,
    "sci-geosciences": 146,
    "sci-visualization": 147,
    "sci-calculators": 148,
    "sci-misc": 149,
    "sci-ml": 150,

    # Games
    "games-emulation": 160,
    "games-engines": 161,
    "games-action": 162,
    "games-arcade": 163,
    "games-board": 164,
    "games-fps": 165,
    "games-rpg": 166,
    "games-strategy": 167,
    "games-puzzle": 168,
    "games-simulation": 169,
    "games-sports": 170,
    "games-roguelike": 171,
    "games-mud": 172,
    "games-server": 173,
    "games-util": 174,
    "games-misc": 175,
    "games-kids": 176,

    # Miscellaneous
    "app-accessibility": 180,
    "app-antivirus": 181,
    "app-cdr": 182,
    "app-eselect": 183,
    "app-laptop": 184,
    "app-metrics": 185,
    "app-mobilephone": 186,
    "app-officeext": 187,
    "app-pda": 188,
    "net-p2p": 189,
    "net-news": 190,
    "net-nntp": 191,
    "net-print": 192,
    "net-proxy": 193,
    "net-voip": 194,
    "net-wireless": 195,
    "net-client": 196,
    "net-nds": 197,
    "net-dialup": 198,
    "sec-policy": 199,
    "www-misc": 200,
    "www-apache": 201,
    "www-apps": 202,
    "www-plugins": 203,
    "gnustep-apps": 204,
    "gnustep-base": 205,
    "gnustep-libs": 206,
    "dev-embedded": 207,
    "dev-games": 208,
    "dev-gap": 209,
    "dev-tex": 210,
    "dev-texlive": 211,

    # Language-specific bindings and packages (lowest priority)
    "dev-cpp": 300,
    "dev-tcltk": 310,
    "dev-dotnet": 320,
    "dev-java": 330,
    "dev-python": 340,
    "dev-ruby": 350,
    "dev-perl": 360,
    "dev-php": 370,
    "dev-go": 380,
    "dev-haskell": 390,
    "dev-lua": 400,
    "dev-lisp": 410,
    "dev-scheme": 420,
    "dev-ml": 430,
    "dev-erlang": 440,
    "dev-elixir": 450,
    "dev-nim": 460,
    "dev-crystal": 470,
    "dev-zig": 480,
    "dev-ada": 490,
    "dev-hare": 500,
    "perl-core": 510,
}
# fmt: on


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


def select_best_category(categories: List[str]) -> str:
    """
    Select the best category for a package based on a predefined priority
    system.

    This function determines which Gentoo category should be preferred when
    multiple matching categories exist. It prioritizes core system categories
    over language bindings.

    Args:
        categories: List of matching categories.

    Returns:
        The highest priority category, or empty string if no categories
        provided.
    """
    if not categories:
        return ""

    if len(categories) == 1:
        return categories[0]

    return min(
        categories,
        key=lambda x: CATEGORY_PRIORITY.get(x, DEFAULT_LOWEST_PRIORITY),
    )


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

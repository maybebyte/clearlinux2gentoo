#!/usr/bin/env python3

"""
Build options processor and compiler configuration generator.
Creates compiler configuration files and processes package-specific flags.

This module converts Clear Linux build options to Gentoo compiler
configurations.
It reads options.conf files from Clear Linux repositories and generates
appropriate Gentoo package.env entries based on mapping data.
"""

import configparser
import json
import os
import sys
from typing import Dict, Union, List, Tuple, Optional


# Path constants
DEFAULT_MAPPING_FILE = "./data/pkg_mapping.json"
DEFAULT_PORTAGE_ENV_DIR = "./etc/portage/env"
DEFAULT_PACKAGE_ENV_DIR = "./etc/portage/package.env"
DEFAULT_CLEARLINUX_REPOS_DIR = "./clearlinux-repos"

# Type aliases
ConfigDict = Dict[str, Dict[str, Union[str, bool, int]]]
GentooPackageMapping = Dict[str, Dict]
CompilerConfigFiles = Dict[str, List[str]]
FlagMapping = List[Tuple[str, str, str, bool]]


def load_package_mapping(
    file_path: str,
) -> GentooPackageMapping:
    """
    Load mapping data from Clear Linux packages to Gentoo packages.

    Args:
        file_path: Path to the JSON mapping file

    Returns:
        Dictionary mapping Clear Linux package names to Gentoo package information
    """
    try:
        with open(file_path, "r", encoding="utf-8") as mapping_file:
            return json.load(mapping_file)
    except FileNotFoundError:
        sys.stderr.write(f"Error: Mapping file '{file_path}' not found\n")
    except json.JSONDecodeError as error:
        sys.stderr.write(f"Error parsing JSON mapping file: {error}\n")
    except Exception as error:
        sys.stderr.write(f"Error loading mapping file: {error}\n")

    return {}


def convert_value(value: str) -> Union[str, bool, int]:
    """
    Convert string values to appropriate types (boolean, integer, or string).

    Args:
        value: The string value to convert

    Returns:
        Converted value as appropriate type
    """
    value_lower = value.lower()
    if value_lower == "true":
        return True
    if value_lower == "false":
        return False

    if value.isdigit():
        return int(value)

    return value


def parse_options_conf(file_path: str) -> ConfigDict:
    """
    Parse an options.conf file into a structured dictionary.

    Args:
        file_path: Path to the options.conf file

    Returns:
        Dictionary with sections and their key-value pairs
    """
    result: ConfigDict = {}

    try:
        config = configparser.ConfigParser(
            empty_lines_in_values=False,
            interpolation=None,
        )
        config.optionxform = str  # type: ignore

        config.read(file_path)

        for section in config.sections():
            result[section] = {}
            for key, value_str in config[section].items():
                if section == "autospec":
                    result[section][key] = convert_value(value_str)
                else:
                    result[section][key] = value_str

        return result

    except configparser.Error as error:
        sys.stderr.write(f"ConfigParser error in {file_path}: {error}\n")
    except FileNotFoundError:
        sys.stderr.write(f"Error: File '{file_path}' not found\n")
    except Exception as error:
        sys.stderr.write(f"Error processing file {file_path}: {error}\n")

    return {}


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Create directory if it doesn't exist.

    Args:
        directory_path: Path to the directory to create

    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as error:
        sys.stderr.write(
            f"Error creating directory {directory_path}: {error}\n"
        )
        return False


def get_compiler_configs() -> CompilerConfigFiles:
    """
    Define the compiler configuration files and their contents.

    Returns:
        Dictionary mapping configuration filenames to their content lines
    """
    return {
        "ffast-math.conf": [
            'CFLAGS="${CFLAGS} -ffast-math"',
            'CXXFLAGS="${CXXFLAGS} -ffast-math"',
            'FCFLAGS="${FCFLAGS} -ffast-math"',
            'FFLAGS="${FFLAGS} -ffast-math"',
        ],
        "funroll.conf": [
            'CFLAGS="${CFLAGS} -falign-functions=32 -fno-semantic-interposition"',
            'CXXFLAGS="${CXXFLAGS} -falign-functions=32 -fno-semantic-interposition"',
            'FCFLAGS="${FCFLAGS} -falign-functions=32 -fno-semantic-interposition"',
            'FFLAGS="${FFLAGS} -falign-functions=32 -fno-semantic-interposition"',
        ],
        "Ofast.conf": [
            'CFLAGS="${CFLAGS} -Ofast"',
            'CXXFLAGS="${CXXFLAGS} -Ofast"',
            'FCFLAGS="${FCFLAGS} -Ofast"',
            'FFLAGS="${FFLAGS} -Ofast"',
        ],
        "Osize.conf": [
            'CFLAGS="${CFLAGS} -Os -ffunction-sections -fdata-sections -fno-semantic-interposition"',
            'CXXFLAGS="${CXXFLAGS} -Os -ffunction-sections -fdata-sections -fno-semantic-interposition"',
            'FCFLAGS="${FCFLAGS} -Os -ffunction-sections -fdata-sections -fno-semantic-interposition"',
            'FFLAGS="${FFLAGS} -Os -ffunction-sections -fdata-sections -fno-semantic-interposition"',
        ],
        "security-sensitive.conf": [
            'CFLAGS="${CFLAGS} -fzero-call-used-regs=used"',
            'CXXFLAGS="${CXXFLAGS} -fzero-call-used-regs=used"',
            'FCFLAGS="${FCFLAGS} -fzero-call-used-regs=used"',
            'FFLAGS="${FFLAGS} -fzero-call-used-regs=used"',
        ],
        "lto.conf": [
            'WARNING_FLAGS="-Werror=odr -Werror=lto-type-mismatch -Werror=strict-aliasing"',
            'CFLAGS="${CFLAGS} -O3 -flto=auto ${WARNING_FLAGS}"',
            'CXXFLAGS="${CXXFLAGS} -O3 -flto=auto ${WARNING_FLAGS}"',
            'FCFLAGS="${FCFLAGS} -O3 -flto=auto ${WARNING_FLAGS}"',
            'FFLAGS="${FFLAGS} -O3 -flto=auto ${WARNING_FLAGS}"',
        ],
        "no-lto.conf": [
            'DISABLE_LTO_FLAGS="-Wno-error=odr -Wno-error=lto-type-mismatch -Wno-error=strict-aliasing -fno-lto"',
            'CFLAGS="${CFLAGS} ${DISABLE_LTO_FLAGS}"',
            'CXXFLAGS="${CXXFLAGS} ${DISABLE_LTO_FLAGS}"',
            'FCFLAGS="${FCFLAGS} ${DISABLE_LTO_FLAGS}"',
            'FFLAGS="${FFLAGS} ${DISABLE_LTO_FLAGS}"',
        ],
    }


def write_compiler_configs(target_dir: str) -> bool:
    """
    Create compiler configuration files in the target directory.

    Args:
        target_dir: Directory to write the configuration files to

    Returns:
        True if all files were written successfully, False otherwise
    """
    if not ensure_directory_exists(target_dir):
        return False

    config_files = get_compiler_configs()

    success = True
    for filename, lines in config_files.items():
        file_path = os.path.join(target_dir, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as config_file:
                for line in lines:
                    config_file.write(f"{line}\n")
        except Exception as error:
            sys.stderr.write(f"Error writing {file_path}: {error}\n")
            success = False

    return success


def find_options_conf_files(base_dir: str) -> List[str]:
    """
    Find all options.conf files recursively in the given directory.

    Args:
        base_dir: Base directory to search in

    Returns:
        List of paths to options.conf files
    """
    options_conf_files = []

    try:
        for root, _, files in os.walk(base_dir):
            if "options.conf" in files:
                options_conf_files.append(os.path.join(root, "options.conf"))
    except Exception as error:
        sys.stderr.write(f"Error searching for options.conf files: {error}\n")

    return options_conf_files


def get_flag_mappings() -> FlagMapping:
    """
    Define mappings between Clear Linux build flags and Gentoo configuration files.

    Returns:
        List of tuples: (flag_name, output_filename, config_file, invert_flag)
    """
    return [
        (
            "security_sensitive",
            "security_sensitive",
            "security-sensitive.conf",
            False,
        ),
        ("funroll-loops", "funroll", "funroll.conf", False),
        ("optimize_size", "Osize", "Osize.conf", False),
        ("fast-math", "ffast-math", "ffast-math.conf", False),
        ("use_lto", "lto", "lto.conf", False),
        ("use_lto", "no-lto", "no-lto.conf", True),
    ]


def process_package_env_entries(
    options_conf_path: str, pkg_mapping: GentooPackageMapping
) -> bool:
    """
    Process an options.conf file and create package.env entries for Gentoo.

    Args:
        options_conf_path: Path to the options.conf file
        pkg_mapping: Dictionary mapping Clear Linux package names to Gentoo package info

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        config = parse_options_conf(options_conf_path)

        if not config or "package" not in config or "autospec" not in config:
            sys.stderr.write(
                f"Invalid config structure in {options_conf_path}\n"
            )
            return False

        clear_pkg_name = config["package"].get("name", "")
        if not clear_pkg_name:
            sys.stderr.write(f"No package name found in {options_conf_path}\n")
            return False

        gentoo_pkg_name = get_gentoo_package_name(clear_pkg_name, pkg_mapping)
        if not gentoo_pkg_name:
            return False

        os.makedirs(DEFAULT_PACKAGE_ENV_DIR, exist_ok=True)

        for flag, filename, conf_file, invert in get_flag_mappings():
            flag_value = config["autospec"].get(flag, False)
            if invert:
                flag_value = not flag_value

            if flag_value:
                file_path = os.path.join(DEFAULT_PACKAGE_ENV_DIR, filename)

                with open(file_path, "a", encoding="utf-8") as env_file:
                    env_file.write(f"{gentoo_pkg_name} {conf_file}\n")

        return True

    except Exception as error:
        sys.stderr.write(f"Error processing {options_conf_path}: {error}\n")
        return False


def get_gentoo_package_name(
    clear_pkg_name: Union[str, int, bool], pkg_mapping: GentooPackageMapping
) -> Optional[str]:
    """
    Get the corresponding Gentoo package name for a Clear Linux package.

    Args:
        clear_pkg_name: Clear Linux package name
        pkg_mapping: Package mapping dictionary

    Returns:
        Gentoo package name or None if not found
    """
    if clear_pkg_name not in pkg_mapping:
        sys.stderr.write(f"No mapping found for package: {clear_pkg_name}\n")
        return None

    gentoo_pkg_info = pkg_mapping[clear_pkg_name]
    gentoo_pkg_name = gentoo_pkg_info.get("gentoo_match", "")

    if not gentoo_pkg_name:
        sys.stderr.write(f"No Gentoo package match for: {clear_pkg_name}\n")
        return None

    return gentoo_pkg_name


def clear_package_env_files(
    package_env_dir: str
) -> bool:
    """
    Clear all package.env files to start fresh.

    Args:
        package_env_dir: Directory containing package.env files

    Returns:
        True if files were cleared successfully, False otherwise
    """
    try:
        if not os.path.exists(package_env_dir):
            return True

        flag_mappings = get_flag_mappings()
        filenames = set(mapping[1] for mapping in flag_mappings)

        for filename in filenames:
            file_path = os.path.join(package_env_dir, filename)
            with open(file_path, "w", encoding="utf-8"):
                pass

        return True

    except Exception as error:
        sys.stderr.write(f"Error clearing package.env files: {error}\n")
        return False


def main():
    """
    Main function to create compiler configs and process options.conf files.

    1. Creates compiler configuration files
    2. Loads package mapping data
    3. Processes options.conf files to generate package.env entries
    """
    if not write_compiler_configs(DEFAULT_PORTAGE_ENV_DIR):
        sys.stderr.write(
            "Failed to create some compiler configuration files\n"
        )
        sys.exit(1)

    pkg_mapping = load_package_mapping(DEFAULT_MAPPING_FILE)
    if not pkg_mapping:
        sys.stderr.write("Failed to load package mapping data\n")
        sys.exit(1)

    options_conf_files = find_options_conf_files(DEFAULT_CLEARLINUX_REPOS_DIR)

    processed_count = 0
    for options_conf_path in options_conf_files:
        if process_package_env_entries(options_conf_path, pkg_mapping):
            processed_count += 1


if __name__ == "__main__":
    main()

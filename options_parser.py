#!/usr/bin/env python3

"""
Build options processor and compiler configuration generator.
Creates compiler configuration files and processes package-specific flags.

This module converts Clear Linux build options to Gentoo compiler
configurations.
It reads options.conf files from Clear Linux repositories and generates
appropriate Gentoo package.env entries based on mapping data.
"""

import argparse
import configparser
import json
import logging
import os
import sys
from typing import Dict, Union, List, Tuple, Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ETC_DIR = os.path.join(BASE_DIR, "etc")

DEFAULT_MAPPING_FILE = os.path.join(DATA_DIR, "pkg_mapping.json")
DEFAULT_PORTAGE_ENV_DIR = os.path.join(ETC_DIR, "portage", "env")
DEFAULT_PACKAGE_ENV_DIR = os.path.join(ETC_DIR, "portage", "package.env")
DEFAULT_CLEARLINUX_REPOS_DIR = os.path.join(BASE_DIR, "clearlinux-repos")

ConfigDict = Dict[str, Dict[str, Union[str, bool, int]]]
GentooPackageMapping = Dict[str, Dict]
CompilerConfigFiles = Dict[str, List[str]]
FlagMapping = List[Tuple[str, str, str, bool]]


def parse_args():
    """
    Parse command-line arguments to allow configuration of paths.

    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="Build options processor")
    parser.add_argument(
        "--mapping-file",
        default=DEFAULT_MAPPING_FILE,
        help="Path to package mapping JSON file",
    )
    parser.add_argument(
        "--portage-env-dir",
        default=DEFAULT_PORTAGE_ENV_DIR,
        help="Path to Portage env directory",
    )
    parser.add_argument(
        "--package-env-dir",
        default=DEFAULT_PACKAGE_ENV_DIR,
        help="Path to package.env directory",
    )
    parser.add_argument(
        "--repos-dir",
        default=DEFAULT_CLEARLINUX_REPOS_DIR,
        help="Path to ClearLinux repositories",
    )
    return parser.parse_args()


def load_package_mapping(
    file_path: str,
) -> GentooPackageMapping:
    """
    Load mapping data from Clear Linux packages to Gentoo packages.

    Args:
        file_path: Path to the JSON mapping file

    Returns:
        Dictionary mapping Clear Linux package names to Gentoo package
        information

    Raises:
        FileNotFoundError: If the mapping file doesn't exist
        json.JSONDecodeError: If the JSON formatting is invalid
    """
    try:
        with open(file_path, "r", encoding="utf-8") as mapping_file:
            return json.load(mapping_file)
    except FileNotFoundError:
        logger.error("Mapping file '%s' not found", file_path)
        raise
    except json.JSONDecodeError as error:
        logger.error("Error parsing JSON mapping file: %s", error)
        raise
    except IOError as error:
        logger.error("IO error reading mapping file: %s", error)
        raise


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

    Raises:
        FileNotFoundError: If the options.conf file doesn't exist
        configparser.Error: If there's an error parsing the config file
    """
    result: ConfigDict = {}

    try:
        config = configparser.ConfigParser(
            empty_lines_in_values=False,
            interpolation=None,
        )
        config.optionxform = str  # type: ignore

        with open(file_path, "r", encoding="utf-8") as config_file:
            config.read_file(config_file)

        for section in config.sections():
            result[section] = {}
            for key, value_str in config[section].items():
                if section == "autospec":
                    result[section][key] = convert_value(value_str)
                else:
                    result[section][key] = value_str

        return result

    except configparser.Error as error:
        logger.error("ConfigParser error in %s: %s", file_path, error)
        raise
    except FileNotFoundError:
        logger.error("File '%s' not found", file_path)
        raise
    except IOError as error:
        logger.error("IO error reading %s: %s", file_path, error)
        raise


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Create directory if it doesn't exist.

    Args:
        directory_path: Path to the directory to create

    Returns:
        True if directory exists or was created

    Raises:
        PermissionError: If there are permission issues creating the directory
        OSError: If there are other OS-related errors
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except PermissionError as error:
        logger.error(
            "Permission denied creating directory %s: %s",
            directory_path,
            error,
        )
        raise
    except OSError as error:
        logger.error(
            "OS error creating directory %s: %s", directory_path, error
        )
        raise


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

    Raises:
        PermissionError: If there are permission issues writing files
        IOError: If there are IO errors during file operations
    """
    ensure_directory_exists(target_dir)
    config_files = get_compiler_configs()

    for filename, lines in config_files.items():
        file_path = os.path.join(target_dir, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as config_file:
                for line in lines:
                    config_file.write(f"{line}\n")
        except PermissionError as error:
            logger.error(
                "Permission denied writing to %s: %s", file_path, error
            )
            return False
        except IOError as error:
            logger.error("IO error writing to %s: %s", file_path, error)
            return False

    return True


def find_options_conf_files(base_dir: str) -> List[str]:
    """
    Find all options.conf files recursively in the given directory.

    Args:
        base_dir: Base directory to search in

    Returns:
        List of paths to options.conf files

    Raises:
        FileNotFoundError: If the base directory doesn't exist
        PermissionError: If there are permission issues accessing directories
    """
    options_conf_files = []

    try:
        for root, _, files in os.walk(base_dir):
            if "options.conf" in files:
                options_conf_files.append(os.path.join(root, "options.conf"))
        return options_conf_files
    except FileNotFoundError:
        logger.error("Base directory not found: %s", base_dir)
        raise
    except PermissionError as error:
        logger.error("Permission denied accessing %s: %s", base_dir, error)
        raise
    except OSError as error:
        logger.error("OS error searching for options.conf files: %s", error)
        raise


def get_flag_mappings() -> FlagMapping:
    """
    Define mappings between Clear Linux build flags and Gentoo configuration
    files.

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
    clear_pkg_str = str(clear_pkg_name)

    if clear_pkg_str not in pkg_mapping:
        logger.warning("No mapping found for package: %s", clear_pkg_str)
        return None

    gentoo_pkg_info = pkg_mapping[clear_pkg_str]
    gentoo_pkg_name = gentoo_pkg_info.get("gentoo_match", "")

    if not gentoo_pkg_name:
        logger.warning("No Gentoo package match for: %s", clear_pkg_str)
        return None

    return gentoo_pkg_name


def process_package_env_entries(
    options_conf_path: str,
    pkg_mapping: GentooPackageMapping,
    package_env_dir: str,
) -> bool:
    """
    Process an options.conf file and create package.env entries for Gentoo.

    Args:
        options_conf_path: Path to the options.conf file
        pkg_mapping: Dictionary mapping Clear Linux package names to Gentoo
        package info
        package_env_dir: Directory to store the generated package.env files

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        config = parse_options_conf(options_conf_path)

        if not config or "package" not in config or "autospec" not in config:
            logger.error("Invalid config structure in %s", options_conf_path)
            return False

        clear_pkg_name = config["package"].get("name", "")
        if not clear_pkg_name:
            logger.error("No package name found in %s", options_conf_path)
            return False

        gentoo_pkg_name = get_gentoo_package_name(clear_pkg_name, pkg_mapping)
        if not gentoo_pkg_name:
            return False

        ensure_directory_exists(package_env_dir)

        for flag, filename, conf_file, invert in get_flag_mappings():
            flag_value = config["autospec"].get(flag, False)
            if invert:
                flag_value = not flag_value

            if flag_value:
                file_path = os.path.join(package_env_dir, filename)
                try:
                    with open(file_path, "a", encoding="utf-8") as env_file:
                        env_file.write(f"{gentoo_pkg_name} {conf_file}\n")
                except IOError as error:
                    logger.error("Error writing to %s: %s", file_path, error)
                    return False

        return True

    except configparser.Error as error:
        logger.error(
            "Config parsing error for %s: %s", options_conf_path, error
        )
        return False
    except FileNotFoundError:
        logger.error("File not found: %s", options_conf_path)
        return False
    except IOError as error:
        logger.error("IO error processing %s: %s", options_conf_path, error)
        return False


def clear_package_env_files(package_env_dir: str) -> bool:
    """
    Clear all package.env files to start fresh.

    Args:
        package_env_dir: Directory containing package.env files

    Returns:
        True if files were cleared successfully, False otherwise
    """
    try:
        ensure_directory_exists(package_env_dir)

        flag_mappings = get_flag_mappings()
        filenames = set(mapping[1] for mapping in flag_mappings)

        for filename in filenames:
            file_path = os.path.join(package_env_dir, filename)
            try:
                with open(file_path, "w", encoding="utf-8"):
                    pass
            except IOError as error:
                logger.error("Error clearing file %s: %s", file_path, error)
                return False

        return True

    except PermissionError as error:
        logger.error(
            "Permission denied accessing %s: %s", package_env_dir, error
        )
        return False
    except OSError as error:
        logger.error("OS error clearing package.env files: %s", error)
        return False


def main():
    """
    Main function to create compiler configs and process options.conf files.

    1. Parses command-line arguments
    2. Creates compiler configuration files
    3. Loads package mapping data
    4. Processes options.conf files to generate package.env entries
    """
    args = parse_args()

    try:
        # Create compiler configuration files
        if not write_compiler_configs(args.portage_env_dir):
            logger.error("Failed to create compiler configuration files")
            sys.exit(1)

        # Load package mapping data
        try:
            pkg_mapping = load_package_mapping(args.mapping_file)
        except (FileNotFoundError, json.JSONDecodeError, IOError) as error:
            logger.error("Failed to load package mapping data: %s", error)
            sys.exit(1)

        # Find options.conf files
        try:
            options_conf_files = find_options_conf_files(args.repos_dir)
        except (FileNotFoundError, PermissionError, OSError) as error:
            logger.error("Failed to find options.conf files: %s", error)
            sys.exit(1)

        # Clear package.env files
        if not clear_package_env_files(args.package_env_dir):
            logger.error("Failed to clear package.env files")
            sys.exit(1)

        # Process options.conf files
        processed_count = 0
        for options_conf_path in options_conf_files:
            if process_package_env_entries(
                options_conf_path, pkg_mapping, args.package_env_dir
            ):
                processed_count += 1

        logger.info(
            "Successfully processed %d out of %d options.conf files",
            processed_count,
            len(options_conf_files),
        )

    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()

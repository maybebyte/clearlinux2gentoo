"""
Build options processor and compiler configuration generator.
Creates compiler configuration files and processes package-specific flags.
"""

import configparser
import json
import os
import sys
from typing import Dict, Union, List


# Type alias for our config dictionary
ConfigDict = Dict[str, Dict[str, Union[str, bool, int]]]


def load_package_mapping(
    file_path: str = "./data/pkg_mapping.json",
) -> Dict[str, Dict]:
    """
    Load package mapping data from JSON file.

    Args:
        file_path: Path to the mapping JSON file

    Returns:
        Dictionary mapping Clear Linux package names to Gentoo package information
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.stderr.write(f"Error: Mapping file '{file_path}' not found\n")
        return {}
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error parsing JSON mapping file: {e}\n")
        return {}
    except Exception as e:
        sys.stderr.write(f"Error loading mapping file: {e}\n")
        return {}  #!/usr/bin/env python3


def convert_value(value: str) -> Union[str, bool, int]:
    """
    Convert string values to appropriate types.

    Args:
        value: The string value to convert

    Returns:
        Converted value as string, boolean or integer
    """
    # Convert boolean values
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    # Convert integer values (only positive integers as per the sample)
    if value.isdigit():
        return int(value)

    # Default case: return as string
    return value


def parse_options_conf(file_path: str) -> ConfigDict:
    """
    Parse an options.conf file using ConfigParser and return a structured dictionary.

    Args:
        file_path: Path to the options.conf file

    Returns:
        A dictionary with sections as keys and dictionaries of key-value pairs as values
    """
    # Initialize empty result with the correct type
    result: ConfigDict = {}

    try:
        # Create ConfigParser object with interpolation disabled to handle % in URLs
        config = configparser.ConfigParser(
            empty_lines_in_values=False, interpolation=None
        )
        # Preserve case in keys
        config.optionxform = str  # type: ignore

        # Read the config file
        config.read(file_path)

        # Convert to dictionary and apply type conversion
        for section in config.sections():
            result[section] = {}
            for key, value_str in config[section].items():
                # Only apply conversions to the autospec section
                if section == "autospec":
                    result[section][key] = convert_value(value_str)
                else:
                    result[section][key] = value_str

        return result

    except configparser.Error as e:
        sys.stderr.write(f"ConfigParser error in {file_path}: {e}\n")
        return {}
    except FileNotFoundError:
        sys.stderr.write(f"Error: File '{file_path}' not found\n")
        return {}
    except Exception as e:
        sys.stderr.write(f"Error processing file {file_path}: {e}\n")
        return {}


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory to create

    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        sys.stderr.write(f"Error creating directory {directory_path}: {e}\n")
        return False


def write_compiler_configs(target_dir: str = "./etc/portage/env") -> bool:
    """
    Create compiler configuration files in the target directory.

    Args:
        target_dir: Directory to write the configuration files to

    Returns:
        True if all files were written successfully, False otherwise
    """
    # Define the configuration files
    config_files = {
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

    # Ensure the target directory exists
    if not ensure_directory_exists(target_dir):
        return False

    # Write each configuration file
    success = True
    for filename, lines in config_files.items():
        file_path = os.path.join(target_dir, filename)
        try:
            with open(file_path, "w") as f:
                for line in lines:
                    f.write(f"{line}\n")
            print(f"Created {file_path}")
        except Exception as e:
            sys.stderr.write(f"Error writing {file_path}: {e}\n")
            success = False

    return success


def find_options_conf_files(base_dir: str) -> List[str]:
    """
    Find all options.conf files in the given directory and its subdirectories.

    Args:
        base_dir: Base directory to search in

    Returns:
        List of paths to options.conf files
    """
    options_conf_files = []

    try:
        for root, dirs, files in os.walk(base_dir):
            if "options.conf" in files:
                options_conf_files.append(os.path.join(root, "options.conf"))
    except Exception as e:
        sys.stderr.write(f"Error searching for options.conf files: {e}\n")

    return options_conf_files


def process_package_env_entries(
    options_conf_path: str, pkg_mapping: Dict[str, Dict]
) -> bool:
    """
    Process an options.conf file and write appropriate package.env entries.

    Args:
        options_conf_path: Path to the options.conf file
        pkg_mapping: Dictionary mapping Clear Linux package names to Gentoo package info

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Parse the options.conf file
        config = parse_options_conf(options_conf_path)

        if not config or "package" not in config or "autospec" not in config:
            sys.stderr.write(
                f"Invalid config structure in {options_conf_path}\n"
            )
            return False

        # Extract Clear Linux package name
        clear_pkg_name = config["package"].get("name", "")
        if not clear_pkg_name:
            sys.stderr.write(f"No package name found in {options_conf_path}\n")
            return False

        # Look up Gentoo package name
        if clear_pkg_name not in pkg_mapping:
            sys.stderr.write(
                f"No mapping found for package: {clear_pkg_name}\n"
            )
            return False

        gentoo_pkg_info = pkg_mapping[clear_pkg_name]
        gentoo_pkg_name = gentoo_pkg_info.get("gentoo_match", "")

        if not gentoo_pkg_name:
            sys.stderr.write(
                f"No Gentoo package match for: {clear_pkg_name}\n"
            )
            return False

        # Ensure package.env directory exists
        package_env_dir = "./etc/portage/package.env"
        os.makedirs(package_env_dir, exist_ok=True)

        # Check for each flag and write to appropriate file
        flag_mappings = [
            (
                "security_sensitive",
                "security_sensitive",
                "security-sensitive.conf",
            ),
            ("funroll-loops", "funroll", "funroll.conf"),
            ("optimize_size", "Osize", "Osize.conf"),
            ("fast-math", "ffast-math", "ffast-math.conf"),
            ("use_lto", "lto", "lto.conf"),
            (
                "use_lto",
                "no-lto",
                "no-lto.conf",
                True,
            ),  # True means invert flag value
        ]

        for mapping in flag_mappings:
            if len(mapping) == 4:
                flag, filename, conf_file, invert = mapping
            else:
                flag, filename, conf_file = mapping
                invert = False

            flag_value = config["autospec"].get(flag, False)
            if invert:
                flag_value = not flag_value

            if flag_value:
                file_path = os.path.join(package_env_dir, filename)

                # Write the entry with Gentoo package name
                with open(file_path, "a") as f:
                    f.write(f"{gentoo_pkg_name} {conf_file}\n")

                print(
                    f"Added {gentoo_pkg_name} to {file_path} (from {clear_pkg_name})"
                )

        return True

    except Exception as e:
        sys.stderr.write(f"Error processing {options_conf_path}: {e}\n")
        return False


def main() -> None:
    """Main function to create compiler configs and process options.conf files."""
    # First create compiler configuration files
    print("Creating compiler configuration files...")
    if not write_compiler_configs():
        sys.stderr.write(
            "Failed to create some compiler configuration files\n"
        )
        sys.exit(1)

    # Load package mapping file
    print("\nLoading package mapping data...")
    pkg_mapping = load_package_mapping()
    if not pkg_mapping:
        sys.stderr.write("Failed to load package mapping data\n")
        sys.exit(1)
    print(f"Loaded mapping data for {len(pkg_mapping)} packages")

    # Find and process options.conf files
    base_dir = "./clearlinux-repos"
    print(f"\nSearching for options.conf files in {base_dir}...")

    options_conf_files = find_options_conf_files(base_dir)
    print(f"Found {len(options_conf_files)} options.conf files")

    # Process each options.conf file
    processed_count = 0
    for options_conf_path in options_conf_files:
        if process_package_env_entries(options_conf_path, pkg_mapping):
            processed_count += 1

    print(
        f"\nSuccessfully processed {processed_count} of {len(options_conf_files)} options.conf files"
    )


if __name__ == "__main__":
    main()

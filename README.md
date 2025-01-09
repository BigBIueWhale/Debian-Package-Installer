
# Debian Package Installer with Dependency Resolver

This project is a Python-based tool for downloading Debian packages along with their dependencies, using Ubuntu repository files.

## Features

- Resolves dependencies recursively for Debian packages.
- Fetches package files from the Ubuntu repository.
- Saves downloaded packages locally for offline use.

## Requirements

- Python 3.x
- `python-debian` library
- `requests` library

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure the `debs/` directory contains valid repository text files:
   - `universe.txt`
   - `main.txt`
   - `multiverse.txt`
   - `restricted.txt`

## Usage

To fetch a package and its dependencies, use the following command:

```bash
python debian-package-installer.py <package_name1> <package_name2> ...
```

### Example
```bash
python debian-package-installer.py ffmpeg
```

### Arguments
- `<package_name>`: Name of the Debian package to fetch.

## Directory Structure

- `debs/`: Directory containing repository text files for dependency resolution.
- `ffmpeg/`: Directory where the downloaded Debian packages are stored.

## How It Works

1. Parses the repository files in the `debs/` directory to extract package URLs.
2. Resolves package dependencies recursively.
3. Downloads all required packages to the `ffmpeg/` directory.

## Notes

- If a package or its dependencies already exist in the `ffmpeg/` directory, they won't be re-downloaded.
- For proper resolution, ensure the repository files in `debs/` are up-to-date.

## Known Issues

- If multiple versions of a package are found, the script chooses the highest lexicographical match.
- Network errors during downloads might require restarting the script.


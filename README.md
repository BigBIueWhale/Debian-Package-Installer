# Debian Package Downloader with Dependency Resolution

This project provides a set of Python tools to download Debian packages and their dependencies from the official Ubuntu repositories.

## Features

-   **Automated Repository Updates**: A script to download and process the latest package lists.
-   **Recursive Dependency Resolution**: Fetches a package and then recursively fetches all its dependencies.
-   **Local Caching**: Saves downloaded `.deb` files locally to avoid re-downloading.
-   **Configurable**: Easily change which Ubuntu suites and components to source packages from.

## Requirements

-   Python 3.x
-   `python-debian` library
-   `requests` library

You can install the required Python libraries using pip:

```bash
python3 -m pip install python-debian requests
```

## Usage

The process is now two steps: first update your local repository index, then download the desired package(s).

Step 1: Update the Repository Index
Before you can download packages, you need to create a local index of available packages. Run the update_repository.py script.
python update_repository.py

This will create a ./repository directory, download the Packages.gz files from the Ubuntu archives, extract them, and save them as .txt files. This step can take a few minutes as it downloads data for multiple Ubuntu suites.

You can customize the sources with command-line arguments:
 * --suites: Change the Ubuntu releases (e.g., noble, jammy).
 * --components: Change the repository sections (e.g., main, universe).
 * --platform: Change the architecture (e.g., binary-arm64).
For example, to only get packages from the 'noble' universe:
python update_repository.py --suites noble --components universe

Step 2: Download a Package and Its Dependencies
Once the repository index is created, use debian-package-installer.py to download a package and all its dependencies.
python debian-package-installer.py <package_name1> <package_name2> ...

Example\
To download ffmpeg and all packages it depends on:
python debian-package-installer.py ffmpeg

The script will read the index files from the ./repository directory, resolve the entire dependency tree, and download all required .deb files into the ./downloaded/ directory.
Directory Structure
 * [update_repository.py](./update_repository.py): Script to download and prepare package lists.
 * [debian-package-installer.py](debian-package-installer.py): Script to download a package and its dependencies.
 * `./repository/`: Directory created by update_repository.py to store the processed package index files.
 * `./downloaded/`: The default output directory where all downloaded .deb packages are stored.
How It Works
 * update_repository.py connects to the Ubuntu archive, downloads the Packages.gz index for each specified suite and component, extracts it, and saves it as a uniquely named text file in the repository/ folder.
 * debian-package-installer.py starts by reading all the text files in repository/ to build a master list of available packages and their download URLs.
 * When given a package name (e.g., ffmpeg), it finds the package in the list, downloads the .deb file, and inspects its metadata to find its dependencies.
 * It then recursively repeats step 3 for each dependency until the entire chain is resolved and downloaded.
Notes
 * If a package (.deb file) already exists in the download directory, it will not be re-downloaded.
 * If multiple versions of a dependency are found across different suites, the script chooses the one that sorts highest lexicographically, which usually corresponds to the newest version.
 * Some dependencies listed may be "virtual packages" which are provided by other concrete packages. The current script may report an error if it cannot find a direct match.

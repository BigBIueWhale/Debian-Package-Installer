# Debian Package Installer

This project provides a set of Python tools to download Debian packages and their dependencies from the official Ubuntu repositories.

## Features

-   **Automated Repository Updates**: A script to download and process the latest package lists.
-   **Recursive Dependency Resolution**: Fetches a package and then recursively fetches all its dependencies.
-   **Local Caching**: Saves downloaded `.deb` files locally to avoid re-downloading.
-   **Configurable**: Easily change which Ubuntu suites and components to source packages from.

## Compare to Alternatives

- **apt-offline**- only downloads the missing packages, not very robust indeed.

- **apt-rdepends**- will cause catastrophic failure when reaching a package name alias.

- **This Project**- works even when running on a different Linux version and/or architecture than the one we're downloading for, and this project downloads **all** dependencies, regardless of whether you (or the target machine) happen to have them installed.

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

**Step 1:** Update the Repository Index
Before you can download packages, you need to create a local index of available packages. Run the update_repository.py script.
python3 update_repository.py

This will create a ./repository directory, download the Packages.gz files from the Ubuntu archives, extract them, and save them as .txt files. This step can take a few minutes as it downloads data for multiple Ubuntu suites.

You can customize the sources with command-line arguments:
 * --base-url: The cloud-hosted folder that contains all Ubuntu releases (for example `https://us.archive.ubuntu.com/ubuntu/ubuntu/dists/bionic/`)
 * --suites: Change the Ubuntu releases (e.g., noble, jammy).
 * --components: Change the repository sections (e.g., main, universe).
 * --platform: Change the architecture (e.g., binary-amd64).
For example (all arguments here are optional, with default values good for newest version of Ubuntu 24.04):
```sh
python3 update_repository.py --base-url https://us.archive.ubuntu.com/ubuntu/dists --suites jammy noble noble-updates noble-security noble-backports --components main restricted universe multiverse
```

**What if my target is not the newest version of Ubuntu 24.04?**:

You will have to match the CLI arguments to `update_repository.py` for your specific `apt sources` file.
```sh
user@ubuntu:/etc/apt/sources.list.d$ cat ubuntu.sources
Types: deb
URIs: http://us.archive.ubuntu.com/ubuntu/
Suites: jammy noble noble-updates noble-security noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
user@ubuntu:/etc/apt/sources.list.d$ 
```


**Step 2:** Download a Package and Its Dependencies
Once the repository index is created, use debian-package-installer.py to download a package and all its dependencies.\
For example (`--base-url` argument is optional, with default value good for newest version of Ubuntu 24.04):
```sh
python3 debian-package-installer.py --base-url https://archive.ubuntu.com/ubuntu --packages <package_name1> <package_name2> ...
```

**Example:** To download ffmpeg and all packages it depends on:
```sh
python3 debian-package-installer.py ffmpeg
```

The script will read the index files from the [./repository/](./repository/) directory, resolve the entire dependency tree, and download all required .deb files into the [./downloaded/](./downloaded/) directory.

Directory Structure:
 * [update_repository.py](./update_repository.py): Script to download and prepare package lists.
 * [debian-package-installer.py](debian-package-installer.py): Script to download a package and its dependencies.
 * [./repository/](./repository/): Directory created by update_repository.py to store the processed package index files.
 * [./downloaded/](./downloaded/): The default output directory where all downloaded .deb packages are stored.


**Raspberry Pi OS Example**

This repo is even more important for Raspberry Pi, because now it means that you don't need a physical online Raspberry Pi to download repos for a Raspberry Pi.

Example system info:
```txt
Raspberry Pi System Overview:

- Device: Raspberry Pi
- OS: Raspberry Pi OS (Bookworm, based on Debian 12)
- Edition: Desktop (Standard)
  - Confirmation:
    - raspberrypi-ui-mods package is installed
    - LibreOffice is not installed (Full edition apps are absent)
- Desktop Environment: Labwc (Wayland-based, using wlroots backend)
- Kernel: Linux 6.12.25-rpt-rpi-2712 #1 SPM PREEMPT Debian 1:6.12.25-1+rpt1 (2025-04-30)
- Architecture: ARM 64-bit (aarch64)
- GUI: Installed and active (not Lite)
- Base Distribution: Debian (as indicated by HOME_URL="https://www.debian.org/")
- Hostname: raspberrypi
- APT Repositories:
  - deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
  - deb http://deb.debian.org/debian-security/ bookworm-security main contrib non-free non-free-firmware
  - deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
  - deb http://archive.raspberrypi.com/debian/ bookworm main
```

```sh
rm -rf ./repository
python3 update_repository.py --base-url http://deb.debian.org/debian/dists --suites bookworm bookworm-updates --components main contrib non-free non-free-firmware --platform binary-arm64
python3 update_repository.py --base-url http://deb.debian.org/debian-security/dists --suites bookworm-security --components main contrib non-free non-free-firmware --platform binary-arm64
python3 update_repository.py --base-url http://archive.raspberrypi.com/debian/dists --suites bookworm --components main --platform binary-arm64
python3 debian-package-installer.py --base-url http://archive.raspberrypi.com/debian,http://deb.debian.org/debian,http://deb.debian.org/debian-security --packages ffmpeg
```

## How It Works
 1. update_repository.py connects to the Ubuntu archive, downloads the Packages.gz index for each specified suite and component, extracts it, and saves it as a uniquely named text file in the repository/ folder.
 2. debian-package-installer.py starts by reading all the text files in repository/ to build a master list of available packages and their download URLs.
 3. When given a package name (e.g., ffmpeg), it finds the package in the list, downloads the .deb file, and inspects its metadata to find its dependencies.
 4. It then recursively repeats step 3 for each dependency until the entire chain is resolved and downloaded.
 5. If a package (.deb file) already exists in the download directory, it will not be re-downloaded.
 6. If multiple versions of a dependency are found across different suites, the script chooses the one that sorts highest, which is the newest version.
 7. Some dependencies listed may be "virtual packages" which are provided by other concrete packages. The current script may report an error if it cannot find a direct match.

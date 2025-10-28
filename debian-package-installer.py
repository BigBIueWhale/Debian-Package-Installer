import os
import requests
from debian.debfile import DebFile
from debian.debian_support import Version
from typing import Set, List
import argparse

DOWNLOAD_DIR = "./downloaded/"
REPO_DIR = "./repository"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def parse_urls_from_text(file_path: str, base_download_url: str) -> List[str]:
    """Parses a repository 'Packages' file to extract relative package paths."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith("Filename: "):
                    # The filename is a relative path like 'pool/universe/f/ffmpeg/ffmpeg_...deb'
                    relative_path = line.split("Filename: ")[1].strip()
                    urls.append(f"{base_download_url}/{relative_path}")
    except FileNotFoundError:
        # This case should be handled by load_all_urls, but is here for safety.
        print(f"Error: Repository file not found: {file_path}")
    except Exception as e:
        print(f"Error reading or parsing file {file_path}: {e}")
    return urls

def load_all_urls(base_download_url: str) -> List[str]:
    """Loads all package URLs from the text files in the repository directory."""
    if not os.path.isdir(REPO_DIR) or not os.listdir(REPO_DIR):
        raise FileNotFoundError(
            f"Repository directory '{REPO_DIR}' not found or is empty.\n"
            f"Please run 'python3 update_repository.py' to download package lists first."
        )
    
    print(f"Loading package lists from '{REPO_DIR}'...")
    text_files = [os.path.join(REPO_DIR, f) for f in os.listdir(REPO_DIR) if f.endswith('.txt')]
    
    all_urls = []
    for text_file in text_files:
        all_urls.extend(parse_urls_from_text(text_file, base_download_url))
    
    if not all_urls:
         raise Exception("No package URLs could be loaded. The repository may be empty or files are unreadable.")
         
    print(f"Loaded {len(all_urls)} package definitions.")
    return all_urls

def find_url_of_dependency(dependency_name: str, deb_urls: List[str]) -> str | None:
    """Finds the best-matching URL for a given package name using version-aware sorting."""
    # Match URLs where the filename part starts with the dependency name.
    # e.g., 'ffmpeg' matches 'ffmpeg_5.1-1_amd64.deb'
    matches = [url for url in deb_urls if url.split('/')[-1].startswith(dependency_name + '_')]

    if not matches:
        # Fallback for packages without version in filename (rare, but possible)
        matches = [url for url in deb_urls if url.split('/')[-1].split('_')[0] == dependency_name]

    if len(matches) > 1:
        # Use a try-except block for robustness in case a filename format is unexpected.
        try:
            # Sort using Debian's versioning rules instead of a naive string sort.
            # The key extracts the version string from the filename (e.g., '6.0-28ubuntu4.1')
            # and converts it to a Version object for proper comparison.
            matches.sort(
                key=lambda url: Version(url.split('/')[-1].split('_')[1]),
                reverse=True
            )
            print(f"Multiple matches found for '{dependency_name}'. Chose: {matches[0].split('/')[-1]}. Instead of: {[match.split('/')[-1] for match in matches[1:]]}")
            return matches[0]
        except (IndexError, TypeError) as e:
            print(f"Warning: Could not parse version for '{dependency_name}'. Defaulting to simple text sort. Error: {e}")
            matches.sort(reverse=True)
            return matches[0]

    elif not matches:
        print(f"Error: No package file found for dependency '{dependency_name}'. It might be a virtual package.")
        return None

    # If there's only one match, return it directly.
    return matches[0]

def fetch_dependency(dep_name: str, visited: Set[str], deb_urls: List[str], base_urls: List[str]) -> List[str]:
    """Downloads a single dependency .deb file and returns its list of further dependencies."""
    url = find_url_of_dependency(dep_name, deb_urls)
    if not url:
        return []
    
    if url in visited:
        # We've already processed this exact file URL, no need to do it again.
        return []
    visited.add(url)
    
    file_name = url.split('/')[-1]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    if os.path.isfile(file_path):
        print(f"Exists: {file_name} is already downloaded.")
    else:
        relative_path = url[len(base_urls[0]) + 1:]
        downloaded = False
        for base in base_urls:
            try_url = f"{base}/{relative_path}"
            print(f"Downloading: {file_name} from {try_url}")
            try:
                response = requests.get(try_url)
                response.raise_for_status()
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                downloaded = True
                break
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch from {try_url}: {e}")
                continue
        if not downloaded:
            raise Exception(f"Error fetching {file_name}: not found in any base URL")

    try:
        deb = DebFile(file_path)
        dependencies_str = deb.debcontrol().get('Depends')
    except Exception as e:
        raise Exception(f"Error processing deb file {file_name}: {e}")

    if dependencies_str:
        # Clean up the dependency string: 'libavcodec58 (>= 7:4.4.2-0ubuntu0.22.04.1), libc6 (>= 2.35)'
        # becomes ['libavcodec58', 'libc6']
        # We only care about the package name, not versions or alternatives ('|')
        deps = [dep.strip().split(' ')[0].split('|')[0].strip() for dep in dependencies_str.split(',')]
        return deps
    
    print(f"Info: '{dep_name}' has no further dependencies.")
    return []

def fetch_dependencies_recursive(initial_name: str, visited: Set[str], deb_urls: List[str], base_urls: List[str]):
    """Recursively fetches a package and all its dependencies."""    
    try:
        dependencies = fetch_dependency(initial_name, visited, deb_urls, base_urls)
        for dep_name in dependencies:
            # Check if we have already processed a package with this name.
            # This is a simple check to avoid infinite recursion on circular dependencies.
            # The `visited` set (with full URLs) is the primary guard.
            if any(initial_name in v for v in visited): 
                fetch_dependencies_recursive(dep_name, visited, deb_urls, base_urls)

    except Exception as e:
        # Catch errors from fetch_dependency and report them with context.
        raise Exception(f"Failed during dependency resolution for '{initial_name}': {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch dependencies for given Debian packages.")
    parser.add_argument(
        '--base-url', 
        type=str, 
        default='https://archive.ubuntu.com/ubuntu',
        help='Comma-separated base URLs to the archives where deb packages are downloaded from'
    )
    parser.add_argument('--packages', nargs='+', help='List of Debian packages to fetch dependencies for.')
    args = parser.parse_args()

    try:
        base_urls = [u.strip() for u in args.base_url.split(',')]
        deb_urls = load_all_urls(base_urls[0])
        visited_urls = set()

        for package_name in args.packages:
            fetch_dependencies_recursive(package_name, visited_urls, deb_urls, base_urls)
        
        print("\nAll dependencies processed.")

    except (FileNotFoundError, Exception) as e:
        raise RuntimeError(f"\nCRITICAL ERROR: {e}")

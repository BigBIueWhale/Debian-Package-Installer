# debian-package-installer.py
import os
import requests
from debian.debfile import DebFile
from typing import Set, List
import argparse

# This URL is now for constructing the final .deb download path
BASE_DOWNLOAD_URL = "https://archive.ubuntu.com/ubuntu" 
DOWNLOAD_DIR = "./downloaded/"
REPO_DIR = "./repository"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def parse_urls_from_text(file_path: str) -> List[str]:
    """Parses a repository 'Packages' file to extract relative package paths."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith("Filename: "):
                    # The filename is a relative path like 'pool/universe/f/ffmpeg/ffmpeg_...deb'
                    relative_path = line.split("Filename: ")[1].strip()
                    urls.append(f"{BASE_DOWNLOAD_URL}/{relative_path}")
    except FileNotFoundError:
        # This case should be handled by load_all_urls, but is here for safety.
        print(f"Error: Repository file not found: {file_path}")
    except Exception as e:
        print(f"Error reading or parsing file {file_path}: {e}")
    return urls

def load_all_urls() -> List[str]:
    """Loads all package URLs from the text files in the repository directory."""
    if not os.path.isdir(REPO_DIR) or not os.listdir(REPO_DIR):
        raise FileNotFoundError(
            f"Repository directory '{REPO_DIR}' not found or is empty.\n"
            f"Please run 'python update_repository.py' to download package lists first."
        )
    
    print(f"Loading package lists from '{REPO_DIR}'...")
    text_files = [os.path.join(REPO_DIR, f) for f in os.listdir(REPO_DIR) if f.endswith('.txt')]
    
    all_urls = []
    for text_file in text_files:
        all_urls.extend(parse_urls_from_text(text_file))
    
    if not all_urls:
         raise Exception("No package URLs could be loaded. The repository may be empty or files are unreadable.")
         
    print(f"Loaded {len(all_urls)} package definitions.")
    return all_urls

def find_url_of_dependency(dependency_name: str, deb_urls: List[str]) -> str | None:
    """Finds the best-matching URL for a given package name."""
    # Match URLs where the filename part starts with the dependency name.
    # e.g., 'ffmpeg' matches 'ffmpeg_5.1-1_amd64.deb'
    matches = [url for url in deb_urls if url.split('/')[-1].startswith(dependency_name + '_')]

    if not matches:
        # Fallback for packages without version in filename (rare, but possible)
        matches = [url for url in deb_urls if url.split('/')[-1].split('_')[0] == dependency_name]

    if len(matches) > 1:
        # Sort to get the "highest" version number, assuming lexicographical order works.
        matches.sort(reverse=True)
        print(f"Warning: Multiple matches found for '{dependency_name}'. Choosing the highest version: {matches[0].split('/')[-1]}")
        return matches[0]
    elif not matches:
        print(f"Error: No package file found for dependency '{dependency_name}'. It might be a virtual package.")
        return None

    return matches[0]

def fetch_dependency(dep_name: str, visited: Set[str], deb_urls: List[str]) -> List[str]:
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
        print(f"Downloading: {file_name}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                file.write(response.content)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching {url}: {e}")

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

def fetch_dependencies_recursive(initial_name: str, visited: Set[str], deb_urls: List[str]):
    """Recursively fetches a package and all its dependencies."""
    print(f"\n--- Resolving: {initial_name} ---")
    
    try:
        dependencies = fetch_dependency(initial_name, visited, deb_urls)
        for dep_name in dependencies:
            # Check if we have already processed a package with this name.
            # This is a simple check to avoid infinite recursion on circular dependencies.
            # The `visited` set (with full URLs) is the primary guard.
            if any(initial_name in v for v in visited): 
                fetch_dependencies_recursive(dep_name, visited, deb_urls)

    except Exception as e:
        # Catch errors from fetch_dependency and report them with context.
        raise Exception(f"Failed during dependency resolution for '{initial_name}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Fetch dependencies for given Debian packages.")
    parser.add_argument('packages', nargs='+', help='List of Debian packages to fetch dependencies for.')
    args = parser.parse_args()

    try:
        deb_urls = load_all_urls()
        visited_urls = set()

        for package_name in args.packages:
            fetch_dependencies_recursive(package_name, visited_urls, deb_urls)
        
        print("\nAll dependencies processed.")

    except (FileNotFoundError, Exception) as e:
        print(f"\nCRITICAL ERROR: {e}")
        # exit(1) # Uncomment to make it a hard failure in scripts

if __name__ == "__main__":
    main()

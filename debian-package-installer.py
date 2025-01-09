import os
import requests
from debian.debfile import DebFile
from typing import Set
import argparse

BASE_URL = "https://archive.ubuntu.com/ubuntu"
DOWNLOAD_DIR = "./ffmpeg/"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def parse_urls_from_text(file_path):
    urls = []
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("Filename: "):
                    filename = line.split("Filename: ")[1].strip()
                    urls.append(f"{BASE_URL}/{filename}")
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    return urls

def load_all_urls():
    #
    text_files = ["debs/universe.txt","debs/main.txt", "debs/multiverse.txt", "debs/restricted.txt"]
    all_urls = []
    for text_file in text_files:
        all_urls.extend(parse_urls_from_text(text_file))
    return all_urls

def find_url_of_dependency(dependency_name, deb_urls):
    matches = [url for url in deb_urls if url.split('/')[-1].split('_')[0] == dependency_name]

    if len(matches) > 1:
        matches.sort(reverse=True)
        print(f"Warning: Multiple matches found for {dependency_name}. Choosing the highest lexicographical match.")
        print(f"Chosen: {matches[0]}")
        return matches[0]
    elif not matches:
        print(f"Error: No match found for {dependency_name}")
        return None

    return matches[0]

def fetch_dependency(dep_name, visited: Set[str], deb_urls):
    url = find_url_of_dependency(dep_name, deb_urls)
    if not url:
        return []
    if url in visited:
        print(f"{dep_name} already fetched")
        return []
    visited.add(url)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    file_name = url.split('/')[-1]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.isfile(file_path):
        print(f"{file_name} already exists")
    else:
        with open(file_path, 'wb') as file:
            file.write(response.content)

    try:
        deb = DebFile(file_path)
        dependencies = deb.debcontrol().get('Depends')
    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        return []

    if dependencies:
        return dependencies.split(', ')
    else:
        print(f"{dep_name} has no dependencies")
        return []

def fetch_dependencies_recursive(initial_name, visited=None, deb_urls=None):
    print(f"Fetching: {initial_name}")
    if visited is None:
        visited = set()
    dependencies = fetch_dependency(initial_name, visited, deb_urls)
    for dep in dependencies:
        dep_name = dep.split(' ')[0]
        fetch_dependencies_recursive(dep_name, visited, deb_urls)

def main():
    parser = argparse.ArgumentParser(description="Fetch dependencies for given Debian packages.")
    parser.add_argument('packages', nargs='+', help='List of Debian packages to fetch dependencies for')
    args = parser.parse_args()

    deb_urls = load_all_urls()

    for package_name in args.packages:
        try:
            fetch_dependencies_recursive(package_name, deb_urls=deb_urls)
        except Exception as e:
            print(f"Error fetching dependencies for {package_name}: {e}")

if __name__ == "__main__":
    main()

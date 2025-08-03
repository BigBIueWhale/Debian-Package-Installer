import os
import shutil
import requests
import gzip
import argparse

REPO_DIR = './repository'

def setup_repository_dir():
    """Deletes the old repository directory if it exists and creates a new empty one."""
    print(f"Setting up fresh repository directory at: {REPO_DIR}")
    if os.path.exists(REPO_DIR):
        try:
            shutil.rmtree(REPO_DIR)
            print(f"Successfully removed existing directory: {REPO_DIR}")
        except OSError as e:
            raise Exception(f"Error removing directory {REPO_DIR}: {e}")
    
    try:
        os.makedirs(REPO_DIR)
        print(f"Successfully created new directory: {REPO_DIR}")
    except OSError as e:
        raise Exception(f"Error creating directory {REPO_DIR}: {e}")

def download_and_extract(url: str, output_path: str):
    """Downloads a .gz file, extracts it, and saves it to the output path."""
    gz_path = os.path.join(REPO_DIR, 'Packages.gz')
    
    try:
        print(f"Downloading: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.HTTPError as e:
        # It's common for some suite/component combos not to exist (e.g., backports/restricted)
        if e.response.status_code == 404:
            print(f"Warning: Not found (404): {url}. Skipping.")
            return
        else:
            raise Exception(f"HTTP Error for {url}: {e}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download {url}: {e}")

    with open(gz_path, 'wb') as f:
        f.write(response.content)

    try:
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"Extracted and saved to: {output_path}")
    except Exception as e:
        raise Exception(f"Failed to extract {gz_path}: {e}")
    finally:
        if os.path.exists(gz_path):
            os.remove(gz_path) # Clean up the downloaded .gz file

def main():
    parser = argparse.ArgumentParser(
        description="Download and prepare Ubuntu package lists for the dependency resolver.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--base-url', 
        type=str, 
        default='https://us.archive.ubuntu.com/ubuntu/dists',
        help='The base URL for the Ubuntu distributions archive.'
    )
    parser.add_argument(
        '--suites', 
        nargs='+', 
        default=['jammy', 'noble', 'noble-updates', 'noble-security', 'noble-backports'],
        help='A space-separated list of Ubuntu suites (e.g., noble noble-updates).'
    )
    parser.add_argument(
        '--components', 
        nargs='+', 
        default=['main', 'restricted', 'universe', 'multiverse'],
        help='A space-separated list of repository components (e.g., main universe).'
    )
    parser.add_argument(
        '--platform', 
        type=str, 
        default='binary-amd64',
        help='The target architecture platform.'
    )
    args = parser.parse_args()

    setup_repository_dir()

    for suite in args.suites:
        for component in args.components:
            url = f"{args.base_url}/{suite}/{component}/{args.platform}/Packages.gz"
            output_filename = f"{suite}-{component}-{args.platform}.txt"
            output_path = os.path.join(REPO_DIR, output_filename)
            
            try:
                download_and_extract(url, output_path)
            except Exception as e:
                print(f"Error processing {suite}/{component}: {e}")
                print("Continuing with the next item...")

    print("\nRepository update process finished.")

if __name__ == "__main__":
    main()

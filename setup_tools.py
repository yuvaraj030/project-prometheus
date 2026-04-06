import urllib.request
import zipfile
import os
import sys

# Define the release URLs for Windows AMD64
nuclei_url = "https://github.com/projectdiscovery/nuclei/releases/download/v3.3.1/nuclei_3.3.1_windows_amd64.zip"
subfinder_url = "https://github.com/projectdiscovery/subfinder/releases/download/v2.6.6/subfinder_2.6.6_windows_amd64.zip"

def download_and_extract(url, zip_name):
    print(f"[*] Downloading {zip_name} from {url}...")
    try:
        urllib.request.urlretrieve(url, zip_name)
        print(f"[*] Extracting {zip_name}...")
        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            zip_ref.extractall(".")
        print(f"[+] Successfully extracted {zip_name}.")
        os.remove(zip_name)
    except Exception as e:
        print(f"[-] Error downloading or extracting {zip_name}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_and_extract(nuclei_url, "nuclei.zip")
    download_and_extract(subfinder_url, "subfinder.zip")
    print("[+] Setup complete. Ready to scan.")

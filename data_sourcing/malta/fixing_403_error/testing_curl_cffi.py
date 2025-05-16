# This script uses curl_cffi to bypass Cloudflare and other protections
# Install with: pip install curl_cffi

from curl_cffi import requests
import os
from pathlib import Path
from urllib.parse import unquote

def download_with_curl_cffi(url, output_path):
    """
    Download file using curl_cffi with browser impersonation to bypass protections
    
    Args:
        url: URL of the file to download
        output_path: Path where to save the file
    
    Returns:
        bool: True if download succeeded, False otherwise
    """
    try:
        print(f"Attempting to download {url} using curl_cffi...")
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Set headers to look more like a real browser
        headers = {
            "Referer": url.split('/Audio/')[0],
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        
        # Try multiple browser impersonations in case one fails
        browser_types = ["chrome110", "chrome107", "safari15_3", "firefox91"]
        
        for browser in browser_types:
            try:
                print(f"Trying with {browser} impersonation...")
                
                # Make request with browser impersonation
                response = requests.get(
                    url, 
                    impersonate=browser,
                    headers=headers,
                    timeout=30
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    # Save the file
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    
                    print(f"Successfully downloaded to {output_path} using {browser} impersonation")
                    return True
                else:
                    print(f"Failed with {browser}: HTTP {response.status_code}")
            
            except Exception as e:
                print(f"Error with {browser}: {str(e)}")
        
        print("All browser impersonations failed")
        return False
        
    except Exception as e:
        print(f"Download failed: {str(e)}")
        return False

if __name__ == "__main__":
    # URL of the MP3 file to download
    mp3_url = "https://parlament.mt/Audio/11thleg/Plenary/Plenary%20001%2010-05-2008%201105hrs.mp3"
    
    # Get filename from URL
    filename = os.path.basename(unquote(mp3_url))
    
    # Output path
    output_file = f"downloads/{filename}"
    
    # Attempt download
    success = download_with_curl_cffi(mp3_url, output_file)
    
    if success:
        print(f"Download complete: {output_file}")
    else:
        print("Download failed. Try installing/updating curl_cffi:")
        print("pip install --upgrade curl_cffi") 
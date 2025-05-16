from playwright.sync_api import sync_playwright
import os, time, random
from pathlib import Path
from urllib.parse import unquote

def download_mp3_with_full_browser(url, output_path):
    with sync_playwright() as p:
        # Create a downloads directory if it doesn't exist
        downloads_dir = os.path.dirname(output_path)
        Path(downloads_dir).mkdir(parents=True, exist_ok=True)
        
        # Launch browser with automatic downloads configured
        browser = p.firefox.launch(headless=False)
        
        # Create a new browser context with download preferences
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
            locale='en-US',
            timezone_id='Europe/London',
            accept_downloads=True  # Enable automatic downloads
        )
        
        # Disable webdriver flag to avoid detection
        context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        """)
        
        page = context.new_page()
        
        # First, visit the main site to establish cookies and session
        main_domain = url.split('/Audio/')[0]
        print(f"Visiting main site first: {main_domain}")
        page.goto(main_domain)
        
        # Simulate realistic human behavior
        for _ in range(3):
            # Random scroll
            page.mouse.wheel(delta_y=random.randint(100, 500), delta_x=0)
            time.sleep(random.uniform(0.5, 1.5))
            # Random mouse movement
            page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            time.sleep(random.uniform(0.3, 1.0))
        
        # Try to download using the expect_download API
        try:
            # Set up download listener
            with page.expect_download(timeout=30000) as download_info:
                print(f"Attempting to navigate to file URL: {url}")
                # Navigate to the MP3 file URL
                page.goto(url)
            
            # Get download info and save file
            download = download_info.value
            print(f"Download started: {download.suggested_filename}")
            
            # Save to the specified output path
            download.save_as(output_path)
            print(f"Successfully downloaded to {output_path}")
            return True
            
        except Exception as e:
            print(f"Automatic download failed: {str(e)}")
            
            # Fallback: Try using browser's context API for direct download
            try:
                print("Trying direct context request method...")
                # Get cookies from current session
                cookies = context.cookies()
                
                # Use context request API with cookies from browser session
                response = context.request.get(url)
                
                if response.ok:
                    with open(output_path, 'wb') as file:
                        file.write(response.body())
                    print(f"Successfully downloaded with context request to {output_path}")
                    return True
                else:
                    print(f"Context request failed: {response.status} {response.status_text}")
                    return False
            except Exception as e:
                print(f"Context request method failed: {str(e)}")
                return False
        finally:
            browser.close()

# Using undetected-chromedriver as an alternative method
def download_with_undetected_chrome(url, output_path):
    try:
        # Only import if needed
        import subprocess
        
        # Create Python script for undetected-chromedriver
        temp_script = "temp_download_script.py"
        with open(temp_script, "w") as f:
            f.write("""
import undetected_chromedriver as uc
import time, os
from selenium.webdriver.common.by import By

url = "{0}"
output_path = "{1}"

options = uc.ChromeOptions()
prefs = {{
    "download.default_directory": os.path.dirname(os.path.abspath(output_path)),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": False
}}
options.add_experimental_option("prefs", prefs)

try:
    driver = uc.Chrome(options=options)
    print("Chrome started")
    
    # First visit the main site
    driver.get("{2}")
    time.sleep(3)
    
    # Then navigate to the file
    print("Navigating to file URL...")
    driver.get(url)
    
    # Wait for download to complete (adjust time as needed)
    print("Waiting for download to complete...")
    time.sleep(20)
    
    print("Download should be complete")
    driver.quit()
    print("Chrome closed")
except Exception as e:
    print(f"Error: {{e}}")
            """.format(url, output_path, url.split('/Audio/')[0]))
        
        # Execute the script
        print("Attempting download with undetected-chromedriver...")
        subprocess.run(["python", temp_script], check=True)
        
        # Check if file exists
        if os.path.exists(output_path) or any(os.path.exists(os.path.join(os.path.dirname(output_path), f)) for f in os.listdir(os.path.dirname(output_path)) if f.endswith(".mp3")):
            print("Download appears successful!")
            return True
        else:
            print("File not found after download attempt")
            return False
            
    except Exception as e:
        print(f"Undetected Chrome download failed: {str(e)}")
        print("You might need to install undetected-chromedriver: pip install undetected-chromedriver")
        return False

# Example usage
if __name__ == "__main__":
    mp3_url = "https://parlament.mt/Audio/11thleg/Plenary/Plenary%20001%2010-05-2008%201105hrs.mp3"
    filename = os.path.basename(unquote(mp3_url))
    output_file = f"downloads/{filename}"
    
    print("Trying browser-based download with Playwright...")
    success = download_mp3_with_full_browser(mp3_url, output_file)
    
    if not success:
        print("Trying with undetected-chromedriver...")
        try:
            success = download_with_undetected_chrome(mp3_url, output_file)
        except:
            print("undetected-chromedriver not available or failed")
            success = False
    
    if not success:
        print("Trying alternative method with system tools...")
        try:
            from testing_system_tools import download_with_system_tool
            success = download_with_system_tool(mp3_url, output_file)
        except:
            print("System tools not available or failed")
            success = False
    
    if not success:
        print("\nALL AUTOMATED METHODS FAILED!")
        print("Possible solutions:")
        print("1. Install undetected-chromedriver: pip install undetected-chromedriver")
        print("2. Try using a VPN to bypass IP restrictions")
        print("3. Try from a different network (mobile hotspot, etc.)")
        print("4. Check if the website requires authentication")

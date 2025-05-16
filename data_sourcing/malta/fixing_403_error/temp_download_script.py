
import undetected_chromedriver as uc
import time, os
from selenium.webdriver.common.by import By

url = "https://parlament.mt/Audio/11thleg/Plenary/Plenary%20001%2010-05-2008%201105hrs.mp3"
output_path = "downloads/Plenary 001 10-05-2008 1105hrs.mp3"

options = uc.ChromeOptions()
prefs = {
    "download.default_directory": os.path.dirname(os.path.abspath(output_path)),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": False
}
options.add_experimental_option("prefs", prefs)

try:
    driver = uc.Chrome(options=options)
    print("Chrome started")
    
    # First visit the main site
    driver.get("https://parlament.mt")
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
    print(f"Error: {e}")
            
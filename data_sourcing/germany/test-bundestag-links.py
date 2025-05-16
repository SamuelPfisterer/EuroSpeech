from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def test_selector():
    driver = webdriver.Chrome()
    driver.get("https://www.bundestag.de/mediathek/plenarsitzungen")
    time.sleep(3)  # Wait for page to load
    
    # Test the selector
    elements = driver.find_elements(By.CLASS_NAME, "bt-open-in-overlay")
    print(f"Found {len(elements)} elements with class 'bt-open-in-overlay'")
    
    # Print details of first 3 elements
    for i, element in enumerate(elements[:3]):
        print(f"\nElement {i+1}:")
        print(f"Text: {element.text}")
        if element.tag_name == 'a':
            print(f"Link: {element.get_attribute('href')}")
        print(f"Class: {element.get_attribute('class')}")
    
    driver.quit()

if __name__ == "__main__":
    test_selector()
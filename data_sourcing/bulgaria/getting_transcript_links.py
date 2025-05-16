import csv
from datetime import datetime
from playwright.sync_api import sync_playwright
import time

def extract_transcript_links():
    # Bulgarian to English month mapping
    MONTH_MAPPING = {
        'януари': 'January',
        'февруари': 'February',
        'март': 'March',
        'април': 'April',
        'май': 'May',
        'юни': 'June',
        'юли': 'July',
        'август': 'August',
        'септември': 'September',
        'октомври': 'October',
        'ноември': 'November',
        'декември': 'December'
    }

    transcript_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto("https://parliament.bg/bg/plenaryst")

        time.sleep(10)

        # More specific selector for year containers
        years = page.query_selector_all("div[data-v-64b176c4].col-12 div.archive-head")
        print(f"Found {len(years)} year elements")

        for year in years:
            year_text = year.inner_text().strip()
            year_num = int(year_text)  # Convert to integer for comparison
            
            if year_num >= 2010:  # Only process years from 2010 onwards
                print(f"Processing year: {year_text}")
                
                # Get the parent div that contains both the year and months
                year_parent = page.query_selector(f"div[data-v-64b176c4].col-12:has(div.archive-head:text-is('{year_text}'))")
                print(f"Found year parent: {year_parent is not None}")
                
                if year_parent:
                    # Get all month spans within this year's container
                    months = year_parent.query_selector_all("ul li span")
                    print(f"Found {len(months)} month elements")

                    for month in months:
                        month_name = month.get_attribute("title")
                        
                        print(f"Processing month: {month_name}")
                        
                        # Convert Bulgarian month name to English
                        english_month = MONTH_MAPPING.get(month_name.lower())
                        if english_month:
                            date = datetime.strptime(f"{english_month} {year_text}", "%B %Y")
                            print(f"Converted date: {date}")
                            try:
                                month.click()
                                
                                # Wait for a link to appear inside the list
                                page.wait_for_selector("ul.p-common-list li a[href*='plenaryst']", timeout=10000)
                                time.sleep(1)  # Reduced to 1 second
                                
                                transcript_links_in_month = page.query_selector_all("ul.p-common-list li a[href*='plenaryst']")
                                print(f"Found {len(transcript_links_in_month)} transcript links for {month_name}")
                                
                                for link in transcript_links_in_month:
                                    href = link.get_attribute("href")
                                    title = link.get_attribute("title")
                                    
                                    transcript_links.append({
                                        "date": title,
                                        "link": f"https://parliament.bg{href}"
                                    })
                                    print(f"Added transcript for date {title}")

                            except Exception as e:
                                print(f"Error processing month {month_name}: {str(e)}")

                            time.sleep(1)  # Reduced pause between months to 1 second

        browser.close()

    return transcript_links

# Save the transcript links to a CSV file
transcript_links = extract_transcript_links()
with open("transcript_links.csv", "w", newline="") as csvfile:
    fieldnames = ["date", "link"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for link in transcript_links:
        writer.writerow(link)

'''

This code uses the Playwright library to automate the process of navigating the website, finding the transcript links, and storing them in a CSV file. Here's how it works:

1. The `extract_transcript_links()` function is defined, which will be responsible for extracting the transcript links.
2. Inside the function, a new Playwright browser instance is launched, and a new page is created.
3. The script navigates to the "https://parliament.bg/bg/plenaryst" URL.
4. It then finds all the years since 2010 and clicks on each one.
5. For each year, it finds all the months and clicks on each one.
6. For each month, it finds all the transcript links and adds them to the `transcript_links` list, along with the date of the transcript.
7. After extracting all the links, the browser is closed.
8. Finally, the `transcript_links` list is saved to a CSV file named "transcript_links.csv" with the date and link for each transcript.

The resulting CSV file will have the following structure:

```
date,link
2010-01-01,https://parliament.bg/bg/plenaryst/id/1234
2010-02-01,https://parliament.bg/bg/plenaryst/id/5678
2010-03-01,https://parliament.bg/bg/plenaryst/id/9012
...
'''
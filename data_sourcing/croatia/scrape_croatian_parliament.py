from playwright.async_api import async_playwright
import csv
from typing import Set, Dict, List
import time
import asyncio
from collections import defaultdict

async def extract_table_data(page) -> List[Dict]:
    """Extract data from the current table view."""
    rows = []
    # Wait for the table to be visible
    await page.wait_for_selector("#ctl00_ContentPlaceHolder_gvFonogrami_DXMainTable", state="visible")
    
    # Get all data rows (excluding header)
    data_rows = await page.locator("#ctl00_ContentPlaceHolder_gvFonogrami_DXMainTable tr[id*='DXDataRow']").all()
    
    for row in data_rows:
        try:
            # Get convocation (first cell)
            convocation_link = row.locator("td a").first
            convocation = await convocation_link.inner_text()
            convocation = convocation.strip()
            
            # Get session (second cell)
            session_cell = row.locator("td:nth-child(2) a")
            session = await session_cell.inner_text()
            session = session.strip()
            
            # Get order number (third cell)
            order_cell = row.locator("td:nth-child(3) a")
            order_no = await order_cell.inner_text()
            order_no = order_no.strip()
            
            # Get transcript link (fifth cell)
            transcript_link = row.locator("td:nth-child(5) a.linkGrid")
            transcript_href = await transcript_link.get_attribute("href")
            full_transcript_url = f"https://edoc.sabor.hr{transcript_href}" if transcript_href.startswith("/") else transcript_href
            
            # Get recording link (sixth cell)
            recording_link = row.locator("td:nth-child(6) a.linkGrid")
            recording_href = await recording_link.get_attribute("href")
            full_recording_url = recording_href  # This URL is already complete
            
            rows.append({
                "convocation": convocation,
                "session": session,
                "order_no": order_no,
                "transcript_url": full_transcript_url,
                "recording_url": full_recording_url
            })
            print(f"Successfully processed: Convocation {convocation}, Session {session}, Order {order_no}")
            
        except Exception as e:
            print(f"Error processing row: {e}")
            continue
            
    return rows

async def scrape_period(browser, period: int, all_data: List[Dict], seen_entries: Set[str]):
    """Scrape a single period in its own context."""
    context = await browser.new_context()
    page = await context.new_page()
    
    print(f"\nProcessing period {period}")
    
    try:
        # Navigate to the starting page
        await page.goto("https://edoc.sabor.hr/Fonogrami.aspx")
        await asyncio.sleep(2)  # Wait for initial load
        
        if period > 0:
            # Click the period selector
            await page.locator("#ctl00_ContentPlaceHolder_navFilter_GHC0").click()
            await asyncio.sleep(1)
            
            # Click the specific period
            next_period_selector = f"#ctl00_ContentPlaceHolder_navFilter_I0i{period}_"
            await page.wait_for_selector(next_period_selector, state="visible")
            await page.locator(next_period_selector).click()
            await asyncio.sleep(10)
        
        # Try to click "Prva" (First) button to ensure we start from the first page
        try:
            first_button = page.get_by_role("cell", name="Prva Prva", exact=True).locator("span")
            if await first_button.is_visible():
                print(f"Period {period}: Clicking 'First' button to start from the beginning")
                await first_button.click()
                await asyncio.sleep(2)
        except Exception as e:
            print(f"Period {period}: Could not find or click 'First' button: {e}")
        
        period_data = []
        while True:
            # Wait for table to load
            await page.wait_for_selector("#ctl00_ContentPlaceHolder_gvFonogrami_DXMainTable", state="visible")
            await asyncio.sleep(2)
            
            # Extract current table data
            current_data = await extract_table_data(page)
            
            # Add new unique entries
            for entry in current_data:
                entry_key = f"{entry['convocation']}-{entry['session']}-{entry['order_no']}"
                if entry_key not in seen_entries:
                    period_data.append(entry)
                    seen_entries.add(entry_key)
            
            # Try to click next button
            next_button = page.get_by_role("cell", name="Sljedeća Sljedeća", exact=True).locator("span")
            if not await next_button.is_visible():
                print(f"Period {period}: Next button not visible, finished with this period")
                break
            
            await next_button.click()
            await asyncio.sleep(2)
        
        print(f"Period {period}: Collected {len(period_data)} entries")
        return period_data
        
    except Exception as e:
        print(f"Error processing period {period}: {e}")
        return []
    finally:
        await context.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        all_data = []
        seen_entries = set()
        
        # Create tasks for all periods
        tasks = []
        for period in range(0, 7):
            task = asyncio.create_task(scrape_period(browser, period, all_data, seen_entries))
            tasks.append(task)
        
        # Wait for all periods to complete and collect results
        results = await asyncio.gather(*tasks)
        
        # Combine all results
        for period_data in results:
            all_data.extend(period_data)
        
        # Save to CSV
        output_file = 'croatian_parliament_data.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['convocation', 'session', 'order_no', 'transcript_url', 'recording_url'])
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"\nData saved to {output_file}")
        print(f"Total entries collected: {len(all_data)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 
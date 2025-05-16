import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import os
from urllib.parse import urljoin

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

async def get_pdf_link(page, url):
    try:
        await page.goto(url)
        
        # Try both possible locations for the PDF link
        pdf_link = await page.evaluate('''() => {
            // First try the minutes-navigation-bar-react
            const navBarLinks = document.querySelectorAll('.minutes-navigation-bar-react a');
            for (const link of navBarLinks) {
                if (link.textContent.includes('PDF')) {
                    return link.href;
                }
            }
            
            // If not found, try the icon-link-list
            const iconListLinks = document.querySelectorAll('.icon-link-list a');
            for (const link of iconListLinks) {
                if (link.textContent.includes('PDF')) {
                    return link.href;
                }
            }
            return null;
        }''')
        
        return pdf_link
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return None

async def process_transcripts(test_mode=True):
    # Read the CSV file
    input_file = os.path.join(SCRIPT_DIR, 'transcript_links_with_dates.csv')
    df = pd.read_csv(input_file)
    
    if test_mode:
        # Sample 5 random rows for testing
        df = df.sample(n=5, random_state=42)
        print("Testing with 5 random links:")
        print(df['link'].to_list())
        print("\n")
    
    # Create a list to store results
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        
        for index, row in df.iterrows():
            url = row['link']
            print(f"Processing {url}")
            
            pdf_link = await get_pdf_link(page, url)
            print(f"Found PDF link: {pdf_link}\n")
            
            results.append({
                'transcript_url': url,
                'pdf_link': pdf_link
            })
        
        await browser.close()
    
    # Save results
    output_file = os.path.join(SCRIPT_DIR, 'pdf_links_test.csv' if test_mode else 'pdf_links.csv')
    final_df = pd.DataFrame(results)
    final_df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(process_transcripts(test_mode=True)) 
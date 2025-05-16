from playwright.sync_api import sync_playwright

def process_transcript_text(url: str) -> str:
    """Process a transcript URL from the Montenegrin Parliament website and return formatted text content.
    
    This function uses Playwright to scrape and process parliamentary session transcripts. It extracts
    speaker information and their corresponding statements, building a formatted text output.
    
    Args:
        url (str): The URL of the transcript page to process. This should be a valid URL from the
                   Montenegrin Parliament website's session pages.
    
    Returns:
        str: A formatted string containing the transcript text, with each speaker's title and
             statements separated by newlines. The format is:
             
             Speaker Title
             Speaker Text
             
             Next Speaker Title
             Next Speaker Text
             
             ...
    
    Raises:
        ValueError: If there is an error during the processing of the transcript, such as:
                   - Network or page loading issues
                   - Missing or malformed page elements
                   - Playwright-related errors
    """
    transcript_text = ""

    try:        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            
            # Wait for content to load
            page.wait_for_selector('div.block.w-full[record="item"][resource="tag"]')
            
            # Find all speaker sections
            speaker_sections = page.query_selector_all('div.block.w-full[record="item"][resource="tag"]')
            
            for section in speaker_sections:
                # Click on the speaker section
                section.click()
                
                # Wait for 2 seconds
                page.wait_for_timeout(2000)
                
                # Extract speaker title
                title_element = section.query_selector('h4.font-sans.text-16.font-bold.pb-2')
                if title_element:
                    speaker_title = f"**{title_element.inner_text()}**"
                else:
                    #print("Error: Could not find speaker title element, setting to empty string")
                    speaker_title = ""
                
                # Extract speaker text
                text_element = page.query_selector('div.flex-1.overflow-y-auto.text-16.text-gray-600.h-48')
                if text_element:
                    speaker_text = text_element.inner_text()
                else:
                    #print("Error: Could not find speaker text element, setting to empty string")
                    speaker_text = ""
                
                # Append speaker title and text to the transcript
                added_text = f"{speaker_title}\n{speaker_text}\n\n"
                #print(f"Adding text: {added_text}")
                transcript_text += added_text
            
            browser.close()
            #print(f"Number of speakers: {len(speaker_sections)}")
            return transcript_text
            
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

# def main():
#     # Example URL - replace with actual URL or get from command line
#     url = "https://www.skupstina.me/en/chronology-of-discussions/482"
    
#     try:
#         processed_text = process_transcript_text(url)
#     except Exception as e:
#         print(f"Error processing transcript: {e}")

# if __name__ == "__main__":
#     main()

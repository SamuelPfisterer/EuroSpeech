from playwright.sync_api import sync_playwright
import re

def process_transcript_text(url: str) -> str:
    """Process a transcript URL and return text content."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            
            # Wait for the content to load
            page.wait_for_selector('div.mt-4')
            
            # Get the div containing the transcript text.
            # There are multiple divs with class mt-4, but it seems that the transcript is always the first one.
            content_div = page.locator('div.mt-4').first
            
            # Extract text content
            text_content = content_div.inner_text()
            
            # Process the text to handle <br> and <b> tags
            # Replace multiple newlines with single newline
            text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
            
            # Clean up any remaining whitespace
            text_content = text_content.strip()
            
            browser.close()
            return text_content
            
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

# def main():
#     # Example URL - replace with actual URL or get from command line
#     url = "https://parliament.bg/bg/plenaryst/ns/55/ID/10973"
    
#     try:
#         processed_text = process_transcript_text_link(url)
        
#         # Save the processed text to a .txt file
#         with open("transcript_output.txt", "w", encoding="utf-8") as f:
#             f.write(processed_text)
        
#         print("Processed text saved to transcript_output.txt")
#     except Exception as e:
#         print(f"Error processing transcript: {e}")

# if __name__ == "__main__":
#     main()
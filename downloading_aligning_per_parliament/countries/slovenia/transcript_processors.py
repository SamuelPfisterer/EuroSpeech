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
            page.wait_for_selector('div[id="viewns_Z7_J9KAJKG10G5G80QTKORJHB08M0_:form1:fieldSet1"]')
            
            # Get the content div
            content_div = page.locator('div[id="viewns_Z7_J9KAJKG10G5G80QTKORJHB08M0_:form1:fieldSet1"]')
            
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
#     url = "https://www.dz-rs.si/wps/portal/Home/seje/evidenca/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8zivSy9Hb283Q0N3E3dLQwCQ7z9g7w8nAwsPE31w9EUGAWZGgS6GDn5BhsYGwQHG-lHEaPfAAdwNCBOPx4FUfiNL8gNDQ11VFQEAF8pdGQ!/dz/d5/L2dBISEvZ0FBIS9nQSEh/?mandat=I&type=sz&uid=6DD17CAD27DDF985C1257832004838ED"
    
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
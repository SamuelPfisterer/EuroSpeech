import sys
import os
from transcript_processors import process_transcript_html, process_transcript_text

def main():
    """Test the transcript processor with a specific URL."""
    # The URL to test
    url = "https://www.parlament.hu:443/web/guest/orszaggyulesi-naplo-elozo-ciklusbeli-adatai?p_p_id=hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_auth=jGdEMTkc&_hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8_pairAction=%2Finternet%2Fcplsql%2Fogy_naplo.ulnap_felszo%3Fp_lista%3DA%26p_nap%3D132%26p_ckl%3D42"
    
    print(f"Testing transcript processor with URL: {url}")
    
    # Create output directory if it doesn't exist
    os.makedirs("test_output", exist_ok=True)
    
    try:
        print("Fetching HTML content...")
        html_content = process_transcript_html(url)
        
        # Save HTML content to file
        with open("test_output/transcript_html.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML content saved to test_output/transcript_html.html ({len(html_content)} bytes)")
        
        print("\nFetching text content...")
        text_content = process_transcript_text(url)
        
        # Save text content to file
        with open("test_output/transcript_text.txt", "w", encoding="utf-8") as f:
            f.write(text_content)
        print(f"Text content saved to test_output/transcript_text.txt ({len(text_content)} bytes)")
        
        # Print first 500 characters of text
        print("\nPreview of extracted text content:")
        print("-" * 80)
        print(text_content[:500] + "...")
        print("-" * 80)
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {str(e)}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
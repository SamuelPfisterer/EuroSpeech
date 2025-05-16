import logging
from transcript_processors import TranscriptProcessor

def main():
    # Initialize the processor
    processor = TranscriptProcessor()
    
    # Test URL for a parliamentary session
    test_url = "https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-126-2017"
    
    try:
        # Process the transcript
        content = processor.process_transcript_text(test_url)
        
        # Save the output to a file
        output_file = "test_transcript_output.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Successfully processed transcript and saved to {output_file}")
        print("\nFirst 500 characters of the output:")
        print("-" * 80)
        print(content[:500])
        print("-" * 80)
        
    except ValueError as e:
        print(f"Error processing transcript: {e}")

if __name__ == "__main__":
    main() 
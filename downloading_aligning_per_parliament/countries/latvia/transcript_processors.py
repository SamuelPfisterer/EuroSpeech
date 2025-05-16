def process_transcript_html(url: str) -> str:
    """Process HTML transcript to extract or clean content."""
    import requests
    from bs4 import BeautifulSoup
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract just the transcript content
    transcript_div = soup.find('div', class_='transcript-content')
    
    if transcript_div:
        return str(transcript_div)
    else:
        return response.text  # Return the whole page if specific content not found 
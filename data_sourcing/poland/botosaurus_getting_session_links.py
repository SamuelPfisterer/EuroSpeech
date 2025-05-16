from botasaurus import *
from bs4 import BeautifulSoup
from botasaurus.request import request, Request

# Base URL template
def generate_links():
    # Return a list instead of using yield
    return [f"https://www.senat.gov.pl/prace/posiedzenia/?k={legislation}&pp=100" 
            for legislation in range(8, 12)]

@request(
    urls=generate_links(),  # Pass URLs directly here
    max_retry=10,
    use_stealth=True  # Add stealth mode for better reliability
)
def scrape_sessions(request: Request, url):  # Changed 'data' to 'url'
    print(f"Scraping URL: {url}")
    response = request.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    results = []
    meetings = soup.find_all('div', class_="meeting container-posiedzenia")
    
    for meeting in meetings:
        # Extracting data from the meeting div
        session_title = meeting.find('h3', class_='meeting-headline').get_text(strip=True)
        session_number = session_title.split('.')[0]
        session_date = meeting.find('div', class_='date-container').find('span').get_text(strip=True)
        
        link_to_session = meeting.find('h3', class_='meeting-headline').find('a')['href']
        link_to_session = f"https://www.senat.gov.pl{link_to_session}"
        
        pdf_link = None
        video_link = None
        transcript_links = []
        
        # Finding PDF and other links
        details = meeting.find_all('div', class_='details')
        for detail in details:
            anchor = detail.find('a')
            
            if anchor:
                link_text = anchor.get_text(strip=True)
                href = f"https://www.senat.gov.pl{anchor['href']}"
                if 'PDF' in link_text:
                    pdf_link = href
                elif 'video' in link_text.lower():
                    video_link = href
        
        # Extracting all transcript links
        menus = meeting.find_all('ul', class_='menu-zakladki-posiedzenia-poziom2')
        for menu in menus:
            day_links = menu.find_all('a')
            for day_link in day_links:
                transcript_links.append(f"https://www.senat.gov.pl{day_link['href']}")

        results.append({
            "session_title": session_title,
            "session_number": session_number,
            "session_date": session_date,
            "link_to_session": link_to_session,
            "pdf_link": pdf_link,
            "transcript_links": transcript_links,
            "video_link": video_link
        })

    return results

if __name__ == "__main__":
    results = scrape_sessions()  # No need to pass arguments here
    all_results = []
    for result in results:  # Combine results from all pages
        if isinstance(result, list):
            all_results.extend(result)
        else:
            all_results.append(result)
    
    print(f"Scraping completed. Found {len(all_results)} sessions.")

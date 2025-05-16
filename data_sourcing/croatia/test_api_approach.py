import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

def get_browser_headers():
    """Return headers that mimic a real browser."""
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def get_form_values(url):
    """Get the necessary form values from the initial page load."""
    try:
        session = requests.Session()
        response = session.get(url, headers=get_browser_headers())
        print("\nInitial GET request status code:", response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print all scripts to find potential AJAX endpoints
        print("\nScripts found:")
        for script in soup.find_all('script'):
            src = script.get('src', '')
            if src:
                print(f"Script source: {src}")
            # Look for any inline scripts that might contain AJAX calls
            if script.string and ('XMLHttpRequest' in script.string or 'ajax' in script.string.lower()):
                print("Found potential AJAX script:")
                print(script.string[:200])
        
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
        eventtarget = soup.find('input', {'name': '__EVENTTARGET'})
        eventargument = soup.find('input', {'name': '__EVENTARGUMENT'})
        
        # Look for any additional hidden fields
        print("\nAll hidden fields found:")
        for hidden in soup.find_all('input', type='hidden'):
            print(f"Hidden field: {hidden.get('name')} = {hidden.get('value', '')[:50]}...")
        
        form_data = {
            '__VIEWSTATE': viewstate['value'] if viewstate else '',
            '__VIEWSTATEGENERATOR': viewstategenerator['value'] if viewstategenerator else '',
            '__EVENTTARGET': eventtarget['value'] if eventtarget else '',
            '__EVENTARGUMENT': eventargument['value'] if eventargument else '',
            # Add any additional ASP.NET fields that might be needed
            'ctl00$ContentPlaceHolder$ScriptManager': 'ctl00$ContentPlaceHolder$UpdatePanel|',
            'ctl00$ContentPlaceHolder$btnTrazi': 'Traži'
        }
        
        print("\nExtracted form values:")
        for key, value in form_data.items():
            print(f"{key}: {value[:50]}..." if value else f"{key}: <empty>")
        
        return form_data, session
    except Exception as e:
        print(f"Error getting form values: {str(e)}")
        return None, None

def try_api_request(url):
    """Attempt to get transcript data via API request."""
    tdrid = url.split('tdrid=')[-1] if 'tdrid=' in url else None
    if not tdrid:
        print("Could not extract tdrid from URL")
        return None
    
    print(f"\nExtracted tdrid: {tdrid}")
    
    form_data, session = get_form_values(url)
    if not form_data or not session:
        print("Could not get form values")
        return None
    
    form_data['tdrid'] = tdrid
    
    api_url = urljoin(url, './FonogramView.aspx')
    print(f"\nConstructed API URL: {api_url}")
    
    try:
        # Try different request approaches
        print("\nTrying different request approaches...")
        
        # Approach 1: Standard POST with session
        headers = get_browser_headers()
        headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'X-MicrosoftAjax': 'Delta=true'
        })
        
        response = session.post(api_url, data=form_data, headers=headers)
        print(f"\nPOST request 1 status code: {response.status_code}")
        
        # Save the response for debugging
        with open('debug_response_1.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\nResponse 1 saved to 'debug_response_1.html'")
        
        # Approach 2: Try with different content type
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        response2 = session.post(api_url, data=form_data, headers=headers)
        print(f"\nPOST request 2 status code: {response2.status_code}")
        
        with open('debug_response_2.html', 'w', encoding='utf-8') as f:
            f.write(response2.text)
        print("\nResponse 2 saved to 'debug_response_2.html'")
        
        # Try to parse both responses
        for idx, resp in enumerate([response, response2], 1):
            print(f"\nAnalyzing response {idx}:")
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            print(f"Found {len(soup.find_all('div'))} total divs")
            print("Div classes found:")
            for div in soup.find_all('div'):
                if div.get('class'):
                    print(div.get('class'))
            
            speech_containers = soup.find_all('div', class_='singleContentContainer')
            if speech_containers:
                print(f"Found {len(speech_containers)} speech containers")
                return resp.text
        
        print("\nNo speech containers found in any response")
        return None
        
    except Exception as e:
        print(f"API request failed: {str(e)}")
        return None

def main():
    test_url = input("Please enter a transcript URL to test: ")
    print("\nTesting API approach with URL:", test_url)
    print("\nAttempting to fetch data...")
    
    content = try_api_request(test_url)
    
    if content:
        print("\nSuccess! Received response with length:", len(content))
    else:
        print("\nFailed to get data through API approach")
        print("\nIt seems the page content is loaded dynamically through JavaScript.")
        print("We might need to use Playwright instead of direct API calls.")

if __name__ == "__main__":
    main() 
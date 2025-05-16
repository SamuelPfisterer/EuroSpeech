import agentql
from playwright.sync_api import sync_playwright
import pandas as pd

with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
    page = agentql.wrap(browser.new_page())
    page.goto("https://av.parlamento.pt/videos/Plenary/16/1")
    QUERY = """
    {
        search_box
    }
    """

    SESSION_LINKS_QUERY = """
    {
        session_recordings[]{
            session_title
            session_number
            session_date
            link_to_session
        }
    }
    """


    count = 0
    session_links_list = []

    

    current_url = page.url
    response = page.query_data(SESSION_LINKS_QUERY)
    session_links = response.get("session_recordings", [])
    session_links_list.extend(session_links)
    print(session_links)
    print(type(session_links))
    

   
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(session_links_list)
    
    # Export to CSV file
    df.to_csv('portugal_session_links.csv', index=False, encoding='utf-8')
    print("Session links have been exported to 'portugal_session_links.csv'")
    



    # Used only for demo purposes. It allows you to see the effect of script.

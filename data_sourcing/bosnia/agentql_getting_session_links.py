import agentql
from playwright.sync_api import sync_playwright
import pandas as pd

with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
    page = agentql.wrap(browser.new_page())
    page.goto("https://parlament.ba/Session/Read?page=1&ConvernerId=1&period=all")
    QUERY = """
    {
        search_box
    }
    """

    SESSION_LINKS_QUERY = """
    {
        session_recordings[]{
            date
            session_title
            link_to_session
        }
    }
    """

    NEXT_PAGE_BUTTON_QUERY = """
    {
        next_page_button
    }
    """

    status = True
    count = 0
    session_links_list = []

    
    while status:
        current_url = page.url
        response = page.query_data(SESSION_LINKS_QUERY)
        session_links = response.get("session_recordings", [])
        session_links_list.extend(session_links)
        print(session_links)
        print(type(session_links))
        try:
            response = page.query_elements(NEXT_PAGE_BUTTON_QUERY)
            next_page_button = response.next_page_button
            if next_page_button is None:
                status = False
            
            next_page_button.click()
            page.wait_for_page_ready_state()
            if current_url == page.url:
                status = False
            count += 1
        except Exception as e:
            print(e)
            status = False

   
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(session_links_list)
    
    # Export to CSV file
    df.to_csv('bosnia_session_links.csv', index=False, encoding='utf-8')
    print("Session links have been exported to 'bosnia_session_links.csv'")
    



    # Used only for demo purposes. It allows you to see the effect of script.

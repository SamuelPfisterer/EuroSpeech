import agentql
from playwright.sync_api import sync_playwright
import pandas as pd
import random

def get_session_links():
    session_links_list = []
    

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,  # Run in non-headless mode for debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',  # Add this to handle potential CORS issues
                '--disable-features=IsolateOrigins',
                '--disable-site-isolation-trials'
            ],
            proxy={
                'server': 'http://gate.smartproxy.com:7000',
                'username': 'sph4b47do7',
                'password': 'fsv5fKD+wvTzLwt628'
        }
    )
        
        # Create a more realistic browser context
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'DNT': '1'
            }
        )
        
        # Add cookies to bypass Cloudflare
        context.add_cookies([
            {
                'name': 'cf_clearance',
                'value': 'IGe9JNkTZFrM69OicfvDJcjltEXj6lfPlpv.xAnupbs-1733902272-1.2.1.1-R2paEbKUw3jU7iCZdD1mmLjTeQmvA5eM374RTO5zRUHx4M_vI3FJM0GuSCv8Sr5PjhCsuDgyaorMRisJOn.ueIg33D6sLgCPivUDEkwljUbEWU5IffvO2lUYRcqISDoqI4oTJmkvhKjA7amAVJfL6CyW0HUMdnnzifNzxJyjN97sJesqIPqC2A.HxDr0L5nYQLJXyYOZMx37b0mkWO9vixesgPf2wpWQZCUdvo_.TLRMrc2.Jz_OBdUA3S.oONJn4GcJ2QomuPV3Kyf2C8fkSHa45UIJty7CbdSt3KY3ykDQByU6ifKtgPao_JD6cI7XHp_CSLBB3TSeWPGVqJBLBAgB9hW7Vj33Sq4OZmQ4G2QF.VEk3pQtkWr_RB48a6v7zVlXd4tOyVob7Tqb_eTYEUc_vuuCMFGQLjQisTr8C1lRVwnM1vrl2VenUQQ2syMfzvwByZOBzjF57j.S0CSJug',
                'domain': '.senat.gov.pl',
                'path': '/'
            }
        ])
        
        page = agentql.wrap(context.new_page())
        
        # Add JavaScript flag to make automation less detectable
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(30000)
        
        # Iterate over legislation periods 8 to 11
        for legislation in range(8, 12):
            base_url = f"https://www.senat.gov.pl/prace/posiedzenia/?k={legislation}&pp=100"
            
            try:
                # Add random delay before each request
                page.wait_for_timeout(random.randint(3000, 7000))
                
                # Navigate with custom waiting strategy
                response = page.goto(base_url, wait_until="networkidle")
                if response is None or response.status >= 400:
                    raise Exception(f"Failed to load page: {base_url}")
                
                # Additional random delay after page load
                page.wait_for_timeout(random.randint(2000, 4000))

                SESSION_LINKS_QUERY = """
                {
                    session_recordings[]{
                        session_title
                        session_number
                        session_date
                        link_to_session
                        pdf_link
                        transcript_links[]
                        video_link
                    }
                }
                """
                
                response = page.query_data(SESSION_LINKS_QUERY)
                session_links = response.get("session_recordings", [])
                
                for session in session_links:
                    session['legislation_period'] = legislation
                    session_links_list.append(session)
                    
                print(f"Collected sessions for legislation period {legislation}")
                
            except Exception as e:
                print(f"Error processing legislation period {legislation}: {str(e)}")
                continue

        df = pd.DataFrame(session_links_list)
        df.to_csv('poland_session_links.csv', index=False, encoding='utf-8')
        print("Session links have been exported to 'poland_session_links.csv'")
        
        context.close()
        browser.close()

if __name__ == "__main__":
    get_session_links()
    



    # Used only for demo purposes. It allows you to see the effect of script.

from botasaurus.request import request, Request

@request(max_retry=10)
def scrape_heading_task(request: Request, data):
    response = request.get('https://www.senat.gov.pl/prace/posiedzenia/?k=8&pp=100')
    print(response.status_code)
    response.raise_for_status()
    return response.text

scrape_heading_task()
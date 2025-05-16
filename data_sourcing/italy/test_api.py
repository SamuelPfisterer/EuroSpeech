import requests
import json

def test_transcript_endpoint(leg="19", docid="1435872", offset=130829):
    # Using the exact URL structure from the browser
    base_url = f"https://www.senato.it/japp/bgt/showdoc/REST/v1/showdoc/get/fragment/{leg}/Resaula/0/{docid}/offset:{offset}"
    
    # Headers exactly matching the browser request
    headers = {
        'authority': 'www.senato.it',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'dnt': '1',
        'origin': 'https://webtv.senato.it',
        'referer': 'https://webtv.senato.it/',
        'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    
    print(f"\n=== Testing with URL: {base_url} ===")
    
    try:
        response = requests.get(base_url, headers=headers)
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        if response.status_code == 200:
            print("\nResponse Text (first 500 characters):")
            print(response.text[:500])
            return response.text
        else:
            print(f"Error: Received status code {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\nError making request: {e}")
        return None

if __name__ == "__main__":
    # Test with the example offset from the browser request
    result = test_transcript_endpoint(offset=130829)
    
    if result:
        print("\nSuccessfully retrieved transcript fragment!")
        # Optionally save to file
        with open("transcript_fragment.html", "w", encoding="utf-8") as f:
            f.write(result)
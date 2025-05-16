import requests
import json
from urllib.parse import quote
from datetime import datetime

def parse_transcript(data):
    """Parse the transcript data into a more useful format"""
    
    # Get metadata
    metadata = {
        'session_id': data['ptk:Poytakirja:attrs'].get('met1:eduskuntaTunnus'),
        'date': data['ptk:Poytakirja:attrs'].get('met1:laadintaPvm'),
        'start_time': data['ptk:Poytakirja:attrs'].get('vsk1:kokousAloitusHetki'),
        'end_time': data['ptk:Poytakirja:attrs'].get('vsk1:kokousLopetusHetki'),
    }
    
    # Extract speeches from the nested structure
    speeches = []
    try:
        # Navigate to the discussion section
        asiakohta = data['ptk:Poytakirja'][0]['vsk:Asiakohta']
        print("\nDebug: Found main section data")
        
        # Find the KeskusteluToimenpide (discussion action)
        keskustelu_item = None
        for item in asiakohta:
            if isinstance(item, dict) and 'vsk:KeskusteluToimenpide' in item:
                keskustelu_item = item
                print("Debug: Found discussion section")
                break
        
        if keskustelu_item:
            # Get the list of speeches
            puheenvuorot = keskustelu_item['vsk:KeskusteluToimenpide']
            
            # Skip the first item (header) and process each speech
            for item in puheenvuorot[1:]:  # Skip the "Keskustelu" header
                if 'vsk:PuheenvuoroToimenpide' in item:
                    speech_data = item['vsk:PuheenvuoroToimenpide']
                    print(f"\nDebug: Processing speech")
                    
                    try:
                        # Get all timing information
                        attrs = speech_data[2]['vsk:PuheenvuoroOsa:attrs']
                        timing = {
                            'display_time': speech_data[0]['vsk1:AjankohtaTeksti'],  # e.g., 13.07
                            'start_time': attrs['vsk1:puheenvuoroAloitusHetki'],     # Full ISO timestamp
                            'end_time': attrs['vsk1:puheenvuoroLopetusHetki'],       # Full ISO timestamp
                            'speech_number': attrs.get('vsk1:puheenvuoroJNro'),      # Speech number in sequence
                        }
                        print(f"Debug: Time information: {timing}")
                        
                        # Get speaker info
                        toimija = speech_data[1]['met:Toimija']
                        henkilo = toimija['org:Henkilo']
                        
                        first_name = henkilo['org1:EtuNimi']
                        last_name = henkilo['org1:SukuNimi']
                        party = henkilo['org1:LisatietoTeksti']
                        print(f"Debug: Found speaker: {first_name} {last_name} ({party})")
                        
                        # Get speech content
                        content = speech_data[2]['vsk:PuheenvuoroOsa']['vsk:KohtaSisalto']
                        paragraphs = []
                        
                        for para in content:
                            if 'sis:KappaleKooste' in para:
                                paragraphs.append(para['sis:KappaleKooste'])
                            elif 'vsk:PuheenjohtajaRepliikki' in para:
                                for reply in para['vsk:PuheenjohtajaRepliikki']:
                                    if 'sis:KappaleKooste' in reply:
                                        paragraphs.append(f"[Chairman: {reply['sis:KappaleKooste']}]")
                        
                        print(f"Debug: Found {len(paragraphs)} paragraphs")
                        
                        # Create speech entry with enhanced timing information
                        speech_entry = {
                            'timing': timing,
                            'speaker': {
                                'first_name': first_name,
                                'last_name': last_name,
                                'party': party
                            },
                            'content': paragraphs
                        }
                        speeches.append(speech_entry)
                        
                    except Exception as e:
                        print(f"Debug: Error processing individual speech: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
        else:
            print("Debug: No discussion section found")
            
    except Exception as e:
        print(f"Error parsing speeches: {e}")
        import traceback
        traceback.print_exc()
    
    result = {
        'metadata': metadata,
        'speeches': speeches
    }
    
    print(f"\nDebug: Found total of {len(speeches)} speeches")
    return result

def get_transcript(session_id, section_number):
    """
    Fetch transcript for a specific session and section
    
    Args:
        session_id (str): Session ID in format 'PTK 125/2024 vp'
        section_number (int): Section number
    """
    # Format session ID correctly (using the format from the working cURL)
    formatted_session_id = session_id.replace(" ", "+").replace("/", "%2F")
    
    # Headers from the working cURL request
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'dnt': '1',
        'referer': 'https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-125-2024',
        'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'cookie': '034003=7zhu/Bix/ljMmrWjNUO96b66uXZqQrOHmuo6JqWyzINNAa6BtW81lzHxDqkV/wzHgM9bmTWahqzeCtGpnKzJ8iwMl2DR/jicTZAK01W8LheGZvqtpAh5JGh8ao0QMVPyf/2NfMHJ2r/J2WkkRlrV+M3tHLkh+oEdC0Qdpm+HnWZmq4Db'
    }
    
    # Construct the API URL (using exact format from cURL)
    url = f'https://verkkolahetys.eduskunta.fi/api/v1/eventmetas/transcripts/{formatted_session_id}/{section_number}'
    print(f"\nTrying URL: {url}")
    
    # Make the request
    response = requests.get(url, headers=headers)
    
    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def print_parsed_transcript(parsed_data):
    """Print the parsed transcript in a readable format"""
    if not parsed_data:
        print("No data to display")
        return
    
    print("\nSession Information:")
    print("=" * 80)
    for key, value in parsed_data['metadata'].items():
        print(f"{key}: {value}")
    
    print("\nSpeeches:")
    print("=" * 80)
    for i, speech in enumerate(parsed_data['speeches'], 1):
        print(f"\nSpeech {i}:")
        print(f"Time: {speech['timing']['display_time']}")
        print(f"Speaker: {speech['speaker']['first_name']} {speech['speaker']['last_name']} ({speech['speaker']['party']})")
        print("Content:")
        for paragraph in speech['content']:
            print(f"  {paragraph}")
        print("-" * 40)

def save_transcript(data, filename):
    """Save transcript data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    session_id = "PTK 125/2024 vp"
    
    # Test without section number
    url_without_section = f"https://verkkolahetys.eduskunta.fi/api/v1/eventmetas/transcripts/{session_id.replace(' ', '+').replace('/', '%2F')}"
    print(f"\nTrying URL without section: {url_without_section}")
    
    # Make request without section number
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'dnt': '1',
        'referer': 'https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-125-2024',
        'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'cookie': '034003=7zhu/Bix/ljMmrWjNUO96b66uXZqQrOHmuo6JqWyzINNAa6BtW81lzHxDqkV/wzHgM9bmTWahqzeCtGpnKzJ8iwMl2DR/jicTZAK01W8LheGZvqtpAh5JGh8ao0QMVPyf/2NfMHJ2r/J2WkkRlrV+M3tHLkh+oEdC0Qdpm+HnWZmq4Db'
    }
    
    response = requests.get(url_without_section, headers=headers)
    
    if response.status_code == 200:
        print("\nSuccessfully fetched data without section")
        data = response.json()
        print("\nResponse structure:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Save the response
        with open('transcript_without_section.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\nSaved complete response to transcript_without_section.json")
    else:
        print(f"\nError: {response.status_code}")
        print(f"Response: {response.text}")
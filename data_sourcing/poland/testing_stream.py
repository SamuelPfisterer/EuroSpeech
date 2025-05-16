import requests
import re
import json

def get_player_script():
    url = "https://r.dcs.redcdn.pl/file/o2/senat/player/2.0.3/js/redgalaxy-senat-player.js"
    response = requests.get(url)
    return response.text

def analyze_player_script():
    script = get_player_script()
    
    # Look for URL patterns
    url_patterns = re.findall(r'https?://[^"\']+redcdn\.pl[^"\']+', script)
    
    # Look for configuration objects
    config_patterns = re.findall(r'{\s*dash:[^}]+}', script)
    
    return {
        'urls': url_patterns,
        'configs': config_patterns
    }

# Example usage
if __name__ == "__main__":
    result = analyze_player_script()
    print(json.dumps(result, indent=4))
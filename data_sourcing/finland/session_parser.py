import json
import datetime
import os
from typing import Dict, List, Optional

class SessionParser:
    def __init__(self, json_data: Dict):
        self.data = json_data
        self.metadata = self._parse_metadata()
        self.speeches = self._parse_all_speeches()
        
    def _parse_metadata(self) -> Dict:
        """Extract session metadata from the JSON data."""
        attrs = self.data.get("ptk:Poytakirja:attrs", {})
        return {
            "session_id": attrs.get("met1:eduskuntaTunnus"),
            "date": attrs.get("met1:laadintaPvm"),
            "start_time": attrs.get("vsk1:kokousAloitusHetki"),
            "end_time": attrs.get("vsk1:kokousLopetusHetki"),
            "language": attrs.get("met1:kieliKoodi")
        }
    
    def _parse_all_speeches(self) -> List[Dict]:
        """Parse all speeches from all sections."""
        all_speeches = []
        
        for item in self.data.get("ptk:Poytakirja", []):
            if "vsk:Asiakohta" in item:
                section_speeches = self._parse_section_speeches(
                    item["vsk:Asiakohta"], 
                    section_type="regular_item"
                )
                all_speeches.extend(section_speeches)
            elif "vsk:MuuAsiakohta" in item:
                section_speeches = self._parse_section_speeches(
                    item["vsk:MuuAsiakohta"],
                    section_type="other_item"
                )
                all_speeches.extend(section_speeches)
                
        return all_speeches
    
    def _parse_section_speeches(self, section_data: List, section_type: str) -> List[Dict]:
        """Parse speeches from a section."""
        speeches = []
        section_number = None
        section_title = None
        
        # First get section metadata
        for item in section_data:
            if "vsk1:KohtaNumero" in item:
                section_number = item["vsk1:KohtaNumero"]
            elif "vsk:KohtaNimeke" in item:
                section_title = item.get("vsk:KohtaNimeke", {}).get("met1:NimekeTeksti")
            elif "sis1:OtsikkoTeksti" in item:
                section_title = item["sis1:OtsikkoTeksti"]
            
            # Parse regular speeches and their chairman comments
            if "vsk:KeskusteluToimenpide" in item:
                for speech_item in item["vsk:KeskusteluToimenpide"]:
                    if isinstance(speech_item, dict):
                        # Parse chairman's introduction if present
                        if "vsk:PuheenjohtajaRepliikki" in speech_item:
                            chairman_speech = self._parse_chairman_statement(
                                speech_item["vsk:PuheenjohtajaRepliikki"],
                                section_number,
                                section_title,
                                speech_item.get("vsk:PuheenvuoroToimenpide:attrs", {}).get("vsk1:puheenvuoroAloitusHetki")
                            )
                            if chairman_speech:
                                speeches.append(chairman_speech)
                        
                        # Parse the main speech
                        if "vsk:PuheenvuoroToimenpide" in speech_item:
                            speech = self._parse_speech(
                                speech_item["vsk:PuheenvuoroToimenpide"],
                                section_number,
                                section_title,
                                speech_item.get("vsk:PuheenvuoroToimenpide:attrs", {})
                            )
                            if speech:
                                speeches.append(speech)
                                
                                # Check for chairman's response within the speech content
                                for content_item in speech_item["vsk:PuheenvuoroToimenpide"]:
                                    if isinstance(content_item, dict) and "vsk:PuheenvuoroOsa" in content_item:
                                        content = content_item["vsk:PuheenvuoroOsa"].get("vsk:KohtaSisalto", [])
                                        for c in content:
                                            if isinstance(c, dict) and "vsk:PuheenjohtajaRepliikki" in c:
                                                chairman_response = self._parse_chairman_statement(
                                                    c["vsk:PuheenjohtajaRepliikki"],
                                                    section_number,
                                                    section_title,
                                                    content_item["vsk:PuheenvuoroOsa:attrs"].get("vsk1:puheenvuoroLopetusHetki")
                                                )
                                                if chairman_response:
                                                    speeches.append(chairman_response)
            
            # Parse standalone chairman statements
            if "vsk:Toimenpide" in item:
                for action in item["vsk:Toimenpide"]:
                    if isinstance(action, dict) and "vsk:KohtaSisalto" in action:
                        for content in action["vsk:KohtaSisalto"]:
                            if isinstance(content, dict) and "vsk:PuheenjohtajaRepliikki" in content:
                                chairman_speech = self._parse_chairman_statement(
                                    content["vsk:PuheenjohtajaRepliikki"],
                                    section_number,
                                    section_title,
                                    None
                                )
                                if chairman_speech:
                                    speeches.append(chairman_speech)
                            
        return speeches
    
    def _parse_chairman_statement(self, chairman_data: List, section_number: Optional[float], section_title: Optional[str], timestamp: Optional[str]) -> Optional[Dict]:
        """Parse a chairman's statement."""
        if not isinstance(chairman_data, list):
            return None
            
        speech_info = {
            "section_number": section_number,
            "section_title": section_title,
            "time": self._format_timestamp(timestamp) if timestamp else None,
            "type": "chairman_statement",
            "timing": {
                "timestamp": timestamp
            },
            "speaker": {
                "name": None,
                "role": "chairman",
                "party": None
            },
            "content": []
        }
        
        for item in chairman_data:
            if "vsk1:PuheenjohtajaTeksti" in item:
                speech_info["speaker"]["name"] = item["vsk1:PuheenjohtajaTeksti"].replace("Puhemies ", "")
            elif "sis:KappaleKooste" in item:
                speech_info["content"].append(item["sis:KappaleKooste"])
        
        # Only return if we have both speaker and content
        if speech_info["speaker"]["name"] and speech_info["content"]:
            return speech_info
        return None
    
    def _format_timestamp(self, timestamp: Optional[str]) -> Optional[str]:
        """Convert ISO timestamp to HH:MM format."""
        if not timestamp:
            return None
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            return dt.strftime("%H:%M")
        except:
            return None
    
    def _parse_speech(self, speech_data: List, section_number: Optional[float], section_title: Optional[str], attrs: Dict = None) -> Optional[Dict]:
        """Parse a single speech."""
        if not isinstance(speech_data, list):
            return None
            
        speech_info = {
            "section_number": section_number,
            "section_title": section_title,
            "time": None,
            "type": "speech",
            "timing": {
                "start_time": attrs.get("vsk1:puheenvuoroAloitusHetki") if attrs else None,
                "end_time": None,
                "speech_type": attrs.get("vsk1:puheenvuoroLuokitusKoodi") if attrs else None
            },
            "speaker": {
                "name": None,
                "party": None,
                "role": None
            },
            "content": []
        }
        
        for item in speech_data:
            if "vsk1:AjankohtaTeksti" in item:
                # Convert time from 13.07 format to HH:MM
                time_str = item["vsk1:AjankohtaTeksti"]
                if isinstance(time_str, (int, float)):
                    hours = int(time_str)
                    minutes = int((time_str % 1) * 100)
                    speech_info["time"] = f"{hours:02d}:{minutes:02d}"
                
            elif "met:Toimija" in item:
                person = item["met:Toimija"].get("org:Henkilo", {})
                speech_info["speaker"]["name"] = f"{person.get('org1:EtuNimi', '')} {person.get('org1:SukuNimi', '')}".strip()
                speech_info["speaker"]["party"] = person.get("org1:LisatietoTeksti", "").lower()
                speech_info["speaker"]["role"] = person.get("org1:AsemaTeksti")
                
            elif "vsk:PuheenvuoroOsa" in item:
                # Get end time from PuheenvuoroOsa:attrs if available
                speech_attrs = item.get("vsk:PuheenvuoroOsa:attrs", {})
                if speech_attrs.get("vsk1:puheenvuoroLopetusHetki"):
                    speech_info["timing"]["end_time"] = speech_attrs["vsk1:puheenvuoroLopetusHetki"]
                
                content = item["vsk:PuheenvuoroOsa"].get("vsk:KohtaSisalto", [])
                for c in content:
                    if isinstance(c, dict) and "sis:KappaleKooste" in c:
                        speech_info["content"].append(c["sis:KappaleKooste"])
        
        # Only return speeches that have both a speaker and content
        if speech_info["speaker"]["name"] and speech_info["content"]:
            return speech_info
        return None

def parse_session_json(json_data: Dict) -> Dict:
    """Parse a parliamentary session JSON into a structured format focusing on speeches."""
    parser = SessionParser(json_data)
    
    # Get speech statistics
    regular_speeches = [s for s in parser.speeches if s["type"] == "speech"]
    chairman_statements = [s for s in parser.speeches if s["type"] == "chairman_statement"]
    
    # Get unique speakers (excluding chairman)
    speakers = []
    for speech in regular_speeches:
        speaker = {
            "name": speech["speaker"]["name"],
            "party": speech["speaker"]["party"]
        }
        if speaker not in speakers:
            speakers.append(speaker)
    
    # Add statistics to metadata
    metadata = parser.metadata
    metadata.update({
        "statistics": {
            "regular_speech_count": len(regular_speeches),
            "chairman_statement_count": len(chairman_statements),
            "total_items": len(parser.speeches)
        },
        "speakers": speakers
    })
    
    return {
        "metadata": metadata,
        "speeches": parser.speeches
    }

if __name__ == "__main__":
    # Example usage
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "transcript_without_section.json")
    output_path = os.path.join(script_dir, "parsed_session.json")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    parsed_data = parse_session_json(data)
    
    # Print statistics
    stats = parsed_data["metadata"]["statistics"]
    print(f"\nSpeech statistics:")
    print(f"Regular speeches: {stats['regular_speech_count']}")
    print(f"Chairman statements: {stats['chairman_statement_count']}")
    print(f"Total items: {stats['total_items']}")
    
    print("\nSpeakers in this session:")
    for speaker in parsed_data["metadata"]["speakers"]:
        print(f"- {speaker['name']} ({speaker['party']})")
    
    # Save parsed data to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nParsed data saved to {output_path}")
    print("\nFirst few regular speeches:")
    regular_speeches = [s for s in parsed_data["speeches"] if s["type"] == "speech"]
    print(json.dumps(regular_speeches[:2], indent=2, ensure_ascii=False)) 
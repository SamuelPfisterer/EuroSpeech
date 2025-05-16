import asyncio
from playwright.sync_api import sync_playwright
import csv

def extract_transcript(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        transcript = []
        speaker_names = page.query_selector_all("a[id*='btnZastupnik']")
        speech_texts = page.query_selector_all("dd.textColor")

        for i, (name, text) in enumerate(zip(speaker_names, speech_texts)):
            speaker = name.inner_text()
            speech = text.inner_text()
            transcript.append({"speaker": speaker, "speech": speech})

        browser.close()
        return transcript

url = "https://edoc.sabor.hr/Views/FonogramView.aspx?tdrid=2016911"
result = extract_transcript(url)

with open('transcript.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['speaker', 'speech'])
    writer.writeheader()
    writer.writerows(result)
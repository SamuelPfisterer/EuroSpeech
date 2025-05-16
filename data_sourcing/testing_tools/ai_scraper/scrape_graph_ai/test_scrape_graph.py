from scrapegraphai.graphs import ScriptCreatorGraph
from scrapegraphai.graphs import ScriptCreatorMultiGraph
from scrapegraphai.builders.graph_builder import GraphBuilder

# Testing all pages at once
'''

prompt = """
- For each possible session since 2010 (you can select it at the top of the search, make sure “All” is selected for month and “The Storting” is selected for report type)
- Go on each transcript link
    - store each transcript link with the video that you can find on the site of the transcript (the second source link is an examplary transcript link)
    - If we go hard: go through each sub page on the transcript (a case usually, or if you can you can don't go through each case but rather Display the entire publication on one page and then go through each text/speech on this side)
        - there for each speech (begins with the name of the speaker), get the text and the link, respectively the time-stamp to the corresponding video
        - the third source link is an example of a "case" page
"""

source = ["https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/?pid=2018-2019&m=all&mt=all", "https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/2018-2019/refs-201819-06-19/"]
config = {
    "llm": {
        "api_key": "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",
        "model": "openai/gpt-4o-mini",
        "max_tokens": 16384},
    "library": "BeautifulSoup"
}

# Create the script creator graph
script_creator = ScriptCreatorMultiGraph(prompt, source, config)

# Run the script creator graph
result = script_creator.run()

print(result)
'''

# Testing scraping the speech segments
prompt = """
I want a script with playwright that does the following: For each speech segment (begins with the name of the speaker), get the text, the speaker name, the time (if given), the video link (if provided), and the time-stamp (if provided)
    - Note that this page is to a large degree in Norwegian
    - the video link is typically in such elements: <a class="ref-innlegg-video icon icon-left icon-video" data-action-start-video="" href="/no/Hva-skjer-pa-Stortinget/videoarkiv/Arkiv-TV-sendinger/?meid=10267&amp;del=1&amp;msid=567">[<time datetime="2019-05-29T10:04:50" class="strtngt_tid">10:04:50</time>]</a>
    - If there are ids for the speech segments, also store them with a clear name
    - Make sure that the Speaker Name and the speech text don't get mixed up!
    - You might not look at the whole page, as there are hundreds of speech segments on one page but the structure should be the same
"""

anthropic_key = "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"

source = "https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/2018-2019/refs-201819-05-29/?all=true"

config = {
    "llm": {
        "api_key": anthropic_key, 
        "model": "anthropic/claude-3-haiku-20240307",
        },
    "library": "playwright"
}

script_creator = ScriptCreatorGraph(prompt, source, config)

result = script_creator.run()

print(result)



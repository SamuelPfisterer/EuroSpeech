from scrapegraphai.graphs import ScriptCreatorGraph


prompt = """
Please create a playwright script that extracts the transcript from the given url. 
Note that I want as a result the speech text and the speaker name for every speech segment
"""

anthropic_key = "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"

source = "https://edoc.sabor.hr/Views/FonogramView.aspx?tdrid=2016911"

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
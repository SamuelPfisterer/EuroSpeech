import requests
from markdownify import markdownify as md
from typing import Callable

def save_markdown(markdown_text, output_path):
    """
    Save markdown text to a file.
    
    Args:
        markdown_text (str): Markdown text to save
        output_path (str): Path to save the markdown file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

def postprocess_markdown(markdown_text: str, *functions: Callable[[str], str]) -> str:
    """
    Applies a sequence of string transformation functions to the given markdown text in order.

    Parameters:
        markdown_text (str): The input markdown text to be processed.
        *functions (Callable[[str], str]): A variable number of functions that each take 
                                           a string as input and return a modified string.

    Returns:
        str: The processed markdown text after applying all functions in order.
    """

    for func in functions:
        markdown_text = func(markdown_text)
    return markdown_text


def process_transcript_text(url: str) -> str:
    """Process a transcript URL and return plain text content in markdown format."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            html_source = response.text
            markdown_text = md(html_source)
            #add arbitrary post-processing functions here
            processed_text = postprocess_markdown(markdown_text, lambda s: s.replace("*", ""))
            return processed_text
        else:
            raise Exception(f"Failed to retrieve page. Status code: {response.status_code}") 
    except Exception as e:
        raise ValueError(f"Failed to process HTML transcript: {str(e)}")
    


# def main():
#     # Example usage
#     
#     markdown_text = process_transcript_html("https://tv.nrsr.sk/archiv/schodza/9/32?MeetingDate=19022025&DisplayChairman=false")
#     print("Converted Markdown:")
#     print(markdown_text)
#     
#     # Save to file
#     save_markdown(markdown_text, "output.md")
#     print("Saved markdown to output.md")
# 
# if __name__ == "__main__":
#     main()


from parliament_transcript_aligner.transcript.preprocessor import DocxPreprocessor, PdfPreprocessor#
import pymupdf
import pymupdf4llm
from PyPDF2 import PdfReader, PdfWriter
from docling.document_converter import DocumentConverter

import sys
original_path = sys.path.copy()
sys.path.append('/usr/itetnas04/data-scratch-01/spfisterer/data/Alignment/testing/own_pipeline')
import my_pymupdf4llm
import pypandoc
# Restore original path after imports
sys.path = original_path


def main(): 
    """
    docx_preprocessor = DocxPreprocessor()
    docx_preprocessor._convert_to_pdf("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/11_001_10052008.doc")
    """
    # get the 10th page of the pdf and save it as page_10.pdf
    """
    reader = PdfReader("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/downloaded_transcript/doc_transcripts/11_007_21052008.pdf")
    writer = PdfWriter()
    writer.add_page(reader.pages[9])
    writer.write("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/page_10.pdf")
    
    converter = DocumentConverter()
    docx_result = converter.convert("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/12_021_21052013.docx")
    markdown_content = docx_result.document.export_to_markdown()
    with open("ouput_docx_markitdown.md", "w") as f:
        f.write(markdown_content)
    
    md = my_pymupdf4llm.to_markdown("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/page_10.pdf", debug_columns=True)
    
    print(md)
    """
    docx_preprocessor = DocxPreprocessor()
    docx_preprocessor.preprocess("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/12_021_21052013.docx")

    #pdf_preprocessor = PdfPreprocessor()
    #pdf_preprocessor.preprocess("/itet-stor/spfisterer/net_scratch/Downloading/countries/malta/downloaded_transcript/doc_transcripts/11_007_21052008.pdf")
    #pdf_preprocessor.preprocess("/itet-stor/spfisterer/net_scratch/Downloading/countries/bosnia-herzegovina/downloaded_transcript/pdf_transcripts/242.pdf")


if __name__ == "__main__":
    main()
from pathlib import Path
import requests
import os
from .base import TranscriptPreprocessor
from .pdf_preprocessor import PdfPreprocessor

class DocxPreprocessor(TranscriptPreprocessor):
    """Preprocessor for DOC and DOCX transcript files."""
    
    CONVERTER_API_URL = "https://doc-converter-ux2v.onrender.com/convert"
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """Check if the file is a DOC or DOCX.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            True if the file has a .doc or .docx extension
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in ['.doc', '.docx']
    
    def _convert_to_pdf(self, file_path: str) -> str:
        """Convert DOC/DOCX file to PDF using the conversion API.
        
        Args:
            file_path: Path to the input document
            
        Returns:
            Path to the converted PDF file
        
        Raises:
            RuntimeError: If conversion fails
        """
        input_path = Path(file_path)
        output_path = input_path.with_suffix('.pdf')
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (input_path.name, f)}
                params = {'format': 'pdf'}
                
                response = requests.post(self.CONVERTER_API_URL, files=files, params=params)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return str(output_path)
            else:
                raise RuntimeError(f"Conversion failed with status code {response.status_code}: {response.text}")
                
        except Exception as e:
            raise RuntimeError(f"Error during conversion: {str(e)}")

    def _convert_to_docx(self, file_path: str) -> str:
        """Convert DOC file to DOCX using the conversion API.
        
        Args:
            file_path: Path to the input document
            
        Returns:
            Path to the converted DOCX file
            
        Raises:
            RuntimeError: If conversion fails
        """
        input_path = Path(file_path)
        output_path = input_path.with_suffix('.docx')
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (input_path.name, f)}
                params = {'format': 'docx'}
                
                response = requests.post(self.CONVERTER_API_URL, files=files, params=params)
                
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return str(output_path)
            else:
                raise RuntimeError(f"Conversion failed with status code {response.status_code}: {response.text}")
                
        except Exception as e:
            raise RuntimeError(f"Error during conversion: {str(e)}")
    
    def preprocess(self, file_path: str) -> str:
        """Preprocess a DOC/DOCX transcript file.
        
        Converts the file to PDF first, then uses PdfPreprocessor.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            Preprocessed transcript text
        """
        
        # Convert to PDF
        pdf_path = self._convert_to_pdf(file_path)
        
        # convert to docx if the file is doc file
        docx_path = file_path
        if Path(file_path).suffix == '.doc':
            docx_path = self._convert_to_docx(file_path)
            
        # convert docx to pdf using pypandoc
        """
        print(f"Converting {docx_path} to PDF with pypandoc")
        pdf_path = f"{Path(file_path).stem}_processed.pdf"
        pypandoc.convert_file(
            docx_path,
            'pdf',
            outputfile=pdf_path
        )
        """
        try:
            # Create a new config with with_docling=True
            updated_config = self.config.copy()
            updated_config['with_docling'] = True
            
            # Use PdfPreprocessor to handle the converted file with updated config to use docling as pypmupdf4llm is not working for malta doxc pdfs for example
            pdf_preprocessor = PdfPreprocessor(config=updated_config, abbreviations=self.abbreviations)
            result = pdf_preprocessor.preprocess(pdf_path)
            
            # Clean up the temporary PDF file unless configured to keep it
            if not self.config.get('keep_temp_files', False):
                Path(pdf_path).unlink(missing_ok=True)
            return result
            
        except Exception as e:
            # Clean up PDF on error
            Path(pdf_path).unlink(missing_ok=True)
            raise e

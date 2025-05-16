import pandas as pd
import sys

def merge_doc_links(csv_path: str) -> None:
    """
    Merge docx_link column into doc_link column in a CSV file.
    Only performs the merge if no row has both columns populated.
    
    Args:
        csv_path: Path to the CSV file to process
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Check if both columns exist
        if 'docx_link' not in df.columns:
            print("No docx_link column found - nothing to merge")
            return
            
        if 'doc_link' not in df.columns:
            print("No doc_link column found - creating it from docx_link")
            df['doc_link'] = df['docx_link']
            df.to_csv(csv_path, index=False)
            return
            
        # Check if any row has both columns populated
        if df[df['doc_link'].notna() & df['docx_link'].notna()].shape[0] > 0:
            print("Found rows with both doc_link and docx_link - aborting merge")
            return
            
        # Perform the merge
        df['doc_link'] = df['doc_link'].combine_first(df['docx_link'])
        
        # Drop the docx_link column
        df = df.drop(columns=['docx_link'])
        
        # Save the modified CSV
        df.to_csv(csv_path, index=False)
        print(f"Successfully merged docx_link into doc_link in {csv_path}")
        
    except Exception as e:
        print(f"Error processing {csv_path}: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_doc_links.py <path_to_csv>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    merge_doc_links(csv_path) 
import os
from pypdf import PdfReader, PdfWriter
import pdfplumber
import pandas as pd
import sys

def remove_blank_pages(input_path, output_path):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            text = page.extract_text()
            if text and text.strip():
                writer.add_page(page)
                
        with open(output_path, "wb") as f:
            writer.write(f)
        print(f"Successfully removed blank pages. Saved to {output_path}")
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)

def extract_tables_to_csv(input_path, output_path):
    try:
        all_data = []
        with pdfplumber.open(input_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        all_data.append(row)
                        
        df = pd.DataFrame(all_data)
        df.to_csv(output_path, index=False, header=False)
        print(f"Successfully extracted data from {input_path} to {output_path}")
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    downloads_pdf = r"C:\Users\aryan\Downloads\aryan (1).pdf"
    downloads_output = r"C:\Users\aryan\Downloads\aryan_fixed.pdf"
    remove_blank_pages(downloads_pdf, downloads_output)
    
    desktop_pdf = r"C:\Users\aryan\OneDrive\Desktop\All readings.pdf"
    data_output = "extracted_readings.csv"
    extract_tables_to_csv(desktop_pdf, data_output)

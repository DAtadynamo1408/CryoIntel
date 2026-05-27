import pdfplumber

def extract_text(input_path, output_path):
    with pdfplumber.open(input_path) as pdf:
        full_text = []
        for page in pdf.pages:
            full_text.append(page.extract_text())
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(full_text))

if __name__ == "__main__":
    extract_text(r"C:\Users\aryan\OneDrive\Desktop\All readings.pdf", "all_readings_text.txt")

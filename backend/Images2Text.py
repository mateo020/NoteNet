from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import io
import re

def extract_text_from_file(file_path):
    """Handle both images and PDF documents with OCR/text extraction"""
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return extract_text_from_image(file_path)
    elif file_path.lower().endswith('.pdf'):
        return process_pdf(file_path)
    else:
        return "Unsupported file format"

def process_pdf(pdf_path):
    """Process PDF files with text extraction and OCR for scanned pages"""
    full_text = []
    
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            if text.strip():  # If text exists
                full_text.append(f"\n=== Page {page_num+1} (Text) ===\n{text}")
            else:  # If scanned page (image)
                full_text.append(f"\n=== Page {page_num+1} (OCR) ===\n{ocr_pdf_page(page)}")
                
        return '\n'.join(full_text)
    except Exception as e:
        return f"PDF Error: {str(e)}"

def ocr_pdf_page(page, dpi=300):
    """Perform OCR on PDF page image"""
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        img_bytes = pix.tobytes("ppm")
        image = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(image)
    except Exception as e:
        return f"OCR Error: {str(e)}"

def extract_text_from_image(image_path):
    """Existing OCR function with improvements"""
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        with Image.open(image_path) as img:
            raw_text = pytesseract.image_to_string(
                img,
                config='--psm 6 --oem 3 -c preserve_interword_spaces=1'
            )
            return clean_and_organize_text(raw_text)
    except Exception as e:
        return f"Image Error: {str(e)}"

def clean_and_organize_text(text):
    """Text cleaning and formatting"""
    text = re.sub(r'[^\w\s\-.,:;!?()\'"@/]', '', text)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    organized = []
    
    for para in paragraphs:
        lines = [line.strip() for line in para.split('\n') if line.strip()]
        if any(re.match(r'^(\d+\.?|[-•*])', line) for line in lines):
            processed = '\n'.join([f"• {line.lstrip('0123456789.-•* ')}" for line in lines])
        else:
            processed = ' '.join(lines)
            if not processed.endswith(('.', '!', '?')):
                processed += '.'
        organized.append(processed)
    
    return '\n\n'.join(organized)

if __name__ == "__main__":
    file_path = "C:/Users/moham/Pictures/Screenshots/Screenshot 2025-02-25 235549.png"  # Test with PDF or image
    extracted_text = extract_text_from_file(file_path)
    
    print("=== DOCUMENT CONTENTS ===")
    print(extracted_text)
    print("\n=== ANALYSIS ===")
    
    words = extracted_text.split()
    sentences = extracted_text.count('.') + extracted_text.count('!') + extracted_text.count('?')
    
    print(f"Total pages: {extracted_text.count('===')//2}")
    print(f"Total words: {len(words)}")
    print(f"Total sentences: {sentences}")
    print(f"Estimated reading time: {len(words)/200:.1f} minutes")
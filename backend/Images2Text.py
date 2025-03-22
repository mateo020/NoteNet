from PIL import Image
import pytesseract

# Explicitly set the Tesseract path (replace if different)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

text = pytesseract.image_to_string(Image.open("C:/Users/moham/Pictures/Screenshots/File.png"))
print(text)
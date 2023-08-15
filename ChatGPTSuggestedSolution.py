# -*- coding: utf-8 -*-
"""
Created on Thu May 18 17:16:37 2023

@author: Armando Anzellini
"""
import PyPDF2
import re
import pytesseract
from pdf2image import convert_from_bytes, convert_from_path
from io import BytesIO

pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'


pdf_dir = 'D:\\Users\\Armando\\OneDrive\\Documents\\AuthorPapers (in progress)\\Forensic Assumptions\\Calibration-PDFs\\'

pdf_path = pdf_dir + 'Trinkaus_1984.pdf'

with open(pdf_path, 'rb') as file:
       
    pdf_reader = PyPDF2.PdfFileReader(file)
    num_pages = pdf_reader.numPages

    lines = []
    # Iterate through each page of the PDF
    for page_num in range(num_pages):
        # Convert the page to an image
        images = convert_from_path(pdf_path, dpi=300, first_page=page_num+1, last_page=page_num+1)
    
        # Perform OCR on each image
        ocr_text = pytesseract.image_to_string(images[0])
    
        # Process the OCR text
        ocr_lines = re.split(r'([A-Z].*?\.)', ocr_text)

        # Filter out lines that represent tables or graphs
        filtered_lines = [line for line in ocr_lines if not all(char.isnumeric() for char in line)]
    
        # Add the filtered lines to the main lines list
        lines += filtered_lines

seen = set()
lines = [line for line in lines if not (line in seen or seen.add(line))]
lines = [re.sub(r'-\n', '', line) for line in lines]
lines = [re.sub(r'\n', ' ', line) for line in lines]
lines = [line.strip() for line in lines]

combined_lines = []
current_sentence = ""

for line in lines:
    line = line.strip()  # Remove leading/trailing whitespace

    if not line.endswith('.'):
        current_sentence +=  line
    else:
        current_sentence +=  line
        combined_lines.append(current_sentence)
        current_sentence = ""



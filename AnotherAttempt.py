# -*- coding: utf-8 -*-
"""
Created on Sun Feb  4 22:05:55 2024

@author: Armando Anzellini
"""
from pdf2image import convert_from_path
from PIL import ImageShow as im
import cv2
import numpy as np
import pytesseract

# identifty tesseract file
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# Convert to PDF to image files
pdf_file = 'D:\\Users\\Armando\\Dropbox\\Academic\\Research\\T&G 90s\\Aiello 1992.pdf'
pages = convert_from_path(pdf_file)

# show images
for page in pages:
    im.show(page)
    
# remove any skew the image may have
def deskew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated

# extract text from image
def extract_text_from_image(image):
    text = pytesseract.image_to_string(image)
    return text

# Create a list to store extracted text from all pages
extracted_text = []

for page in pages:
    # Step 2: Preprocess the image (deskew)
    preprocessed_image = deskew(np.array(page))

    # Step 3: Extract text using OCR
    text = extract_text_from_image(preprocessed_image)
    extracted_text.append(text)
    

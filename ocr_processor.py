"""
OCR Processing Module
Uses Tesseract OCR to extract and parse text from ID documents and address proofs
"""
import cv2
import pytesseract
import re
from typing import Dict, Optional
from datetime import datetime
import os


class OCRProcessor:
    """Handles OCR text extraction and parsing from identity documents"""
    
    def __init__(self):
        """Initialize OCR processor with Tesseract configuration"""
        # Set Tesseract path if specified in environment
        tesseract_cmd = os.getenv("TESSERACT_CMD")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def preprocess_image(self, image):
        """
        Preprocess image for better OCR accuracy
        - Convert to grayscale
        - Apply thresholding
        - Denoise if needed
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding for better text extraction
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # Optional: denoise
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
        return denoised
    
    def extract_text(self, image) -> str:
        """
        Extract text from image using Tesseract OCR
        Uses preprocessing for improved accuracy
        """
        try:
            # Preprocess image
            processed = self.preprocess_image(image)
            
            # Extract text using pytesseract
            # Use config for better accuracy with English text
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(processed, config=custom_config)
            
            return text
        except Exception as e:
            print(f"OCR extraction error: {str(e)}")
            return ""
    
    def parse_voter_id(self, text: str) -> Dict[str, Optional[str]]:
        """
        Parse voter ID text to extract structured fields:
        - Name
        - Date of Birth
        - ID Number
        - Address (if present)
        """
        parsed = {
            "name": None,
            "date_of_birth": None,
            "id_number": None,
            "address": None
        }
        
        lines = text.split('\n')
        text_lower = text.lower()
        
        # Extract Name - typically appears after "name" keyword
        name_patterns = [
            r'name[:\s]+([a-z\s.]+)',
            r'holder[:\s]+([a-z\s.]+)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                parsed["name"] = match.group(1).strip()
                break
        
        # Extract Date of Birth - various formats (DD/MM/YYYY, DD-MM-YYYY, etc.)
        dob_patterns = [
            r'(?:dob|date of birth|birth)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'born[:\s]+(\d{1,2}\s+[a-z]+\s+\d{4})'
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["date_of_birth"] = match.group(1).strip()
                break
        
        # Extract ID Number - alphanumeric patterns
        id_patterns = [
            r'(?:id|epic|voter)[:\s#]*([a-z]{3}\d{7})',  # Format: ABC1234567
            r'(?:number|no)[:\s#]*([a-z0-9]{8,15})',
            r'\b([A-Z]{3}\d{7})\b'
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["id_number"] = match.group(1).strip().upper()
                break
        
        # Extract Address - typically multi-line after "address" keyword
        address_match = re.search(
            r'address[:\s]+((?:[^\n]+\n?){1,4})',
            text,
            re.IGNORECASE
        )
        if address_match:
            parsed["address"] = address_match.group(1).strip()
        
        return parsed
    
    def parse_address_proof(self, text: str) -> Dict[str, Optional[str]]:
        """
        Parse address proof document (utility bill, bank statement, etc.)
        Extract:
        - Name
        - Address
        - Document date
        """
        parsed = {
            "name": None,
            "address": None,
            "document_date": None
        }
        
        lines = text.split('\n')
        
        # Extract Name - look for capitalized names
        name_patterns = [
            r'(?:to|name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][A-Z\s]{10,30})',  # All caps names
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                parsed["name"] = match.group(1).strip()
                break
        
        # Extract Address - look for multi-line address patterns
        # Typically contains street, city, pin/zip
        address_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for lines with address indicators
            if any(keyword in line.lower() for keyword in ['street', 'road', 'avenue', 'city', 'pin', 'zip']):
                # Capture this line and next 2-3 lines
                address_lines = lines[i:i+3]
                break
        
        if address_lines:
            parsed["address"] = ' '.join([l.strip() for l in address_lines if l.strip()])
        
        # If no address found by keywords, look for pin/zip code pattern
        if not parsed["address"]:
            pin_match = re.search(
                r'([^\n]+(?:\d{6}|\d{5}))',  # Line containing 6 or 5 digit pin
                text
            )
            if pin_match:
                # Get surrounding context
                start = max(0, pin_match.start() - 100)
                end = min(len(text), pin_match.end() + 50)
                parsed["address"] = text[start:end].replace('\n', ' ').strip()
        
        # Extract Document Date
        date_patterns = [
            r'date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}\s+[a-z]+\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["document_date"] = match.group(1).strip()
                break
        
        return parsed
    
    def normalize_date(self, date_string: str) -> Optional[str]:
        """
        Normalize date strings to YYYY-MM-DD format
        Handles various input formats
        """
        if not date_string:
            return None
        
        date_formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d %B %Y",
            "%d %b %Y"
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None

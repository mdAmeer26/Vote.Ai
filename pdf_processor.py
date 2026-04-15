"""
PDF Processor for Voter Data Analysis
Handles extraction of voter information from PDF documents in multiple languages
"""

import pdfplumber
import pytesseract
from PIL import Image
import io
import re
from typing import List, Dict, Any, Optional
from langdetect import detect, LangDetectException
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Process PDF documents containing voter data"""
    
    # Language code mapping for Tesseract
    LANGUAGE_MAPPING = {
        'en': 'eng',      # English
        'hi': 'hin',      # Hindi
        'bn': 'ben',      # Bengali
        'te': 'tel',      # Telugu
        'ta': 'tam',      # Tamil
        'mr': 'mar',      # Marathi
        'gu': 'guj',      # Gujarati
        'kn': 'kan',      # Kannada
        'ml': 'mal',      # Malayalam
        'pa': 'pan',      # Punjabi
        'ur': 'urd',      # Urdu
        'or': 'ori',      # Oriya
        'as': 'asm',      # Assamese
    }
    
    def __init__(self):
        """Initialize PDF processor"""
        self.detected_languages = set()
        
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF using pdfplumber
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            result = {
                'text': '',
                'pages': [],
                'tables': [],
                'languages': [],
                'total_pages': 0
            }
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                result['total_pages'] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_data = {
                        'page_number': page_num,
                        'text': '',
                        'tables': []
                    }
                    
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        page_data['text'] = page_text
                        result['text'] += f"\n\n--- Page {page_num} ---\n\n{page_text}"
                        
                        # Detect language
                        try:
                            lang = detect(page_text)
                            if lang not in result['languages']:
                                result['languages'].append(lang)
                                self.detected_languages.add(lang)
                        except LangDetectException:
                            pass
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_data = {
                                'page': page_num,
                                'table_index': table_idx,
                                'data': table
                            }
                            page_data['tables'].append(table_data)
                            result['tables'].append(table_data)
                    
                    result['pages'].append(page_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return {
                'text': '',
                'pages': [],
                'tables': [],
                'languages': [],
                'total_pages': 0,
                'error': str(e)
            }
    
    def extract_images_from_pdf(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Extract images from PDF pages for OCR processing
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            List of PIL Image objects
        """
        images = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    # Convert page to image
                    img = page.to_image(resolution=300)
                    pil_image = img.original
                    images.append(pil_image)
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {str(e)}")
        
        return images
    
    def ocr_pdf_with_language(self, pdf_bytes: bytes, languages: Optional[List[str]] = None) -> str:
        """
        Perform OCR on PDF with multi-language support
        Enhanced with image preprocessing for better accuracy
        
        Args:
            pdf_bytes: PDF file as bytes
            languages: List of language codes (e.g., ['en', 'hi'])
            
        Returns:
            Extracted text from OCR
        """
        if languages is None:
            languages = ['eng']  # Default to English
        else:
            # Convert language codes to Tesseract format
            languages = [self.LANGUAGE_MAPPING.get(lang, 'eng') for lang in languages]
        
        lang_string = '+'.join(languages)
        
        try:
            images = self.extract_images_from_pdf(pdf_bytes)
            ocr_text = ""
            
            for idx, image in enumerate(images, 1):
                try:
                    # Preprocess image for better OCR
                    processed_image = self.preprocess_image_for_ocr(image)
                    
                    # Perform OCR with custom config for better table detection
                    custom_config = r'--oem 3 --psm 6'  # PSM 6: Assume a single uniform block of text
                    text = pytesseract.image_to_string(processed_image, lang=lang_string, config=custom_config)
                    ocr_text += f"\n\n--- Page {idx} (OCR) ---\n\n{text}"
                    
                    logger.info(f"OCR completed for page {idx}, extracted {len(text)} characters")
                except Exception as e:
                    logger.error(f"OCR error on page {idx}: {str(e)}")
                    ocr_text += f"\n\n--- Page {idx} (OCR Failed) ---\n\n"
            
            return ocr_text
            
        except Exception as e:
            logger.error(f"Error in OCR processing: {str(e)}")
            return ""
    
    def preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            import cv2
            import numpy as np
            
            # Convert PIL to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if not already
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply thresholding to get black text on white background
            # Using Otsu's thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(binary, h=10)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(denoised)
            
            return processed_image
            
        except Exception as e:
            logger.warning(f"Error preprocessing image, using original: {str(e)}")
            return image
    
    def parse_voter_data_from_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Parse voter data from extracted table
        
        Args:
            table: 2D list representing table data
            
        Returns:
            List of voter records as dictionaries
        """
        if not table or len(table) < 2:
            return []
        
        voters = []
        headers = [str(h).lower().strip() if h else '' for h in table[0]]
        
        # Common header variations
        name_headers = ['name', 'voter name', 'full name', 'नाम', 'naam']
        dob_headers = ['dob', 'date of birth', 'birth date', 'जन्म तिथि', 'janma tithi']
        id_headers = ['id', 'voter id', 'epic no', 'id number', 'पहचान संख्या']
        address_headers = ['address', 'residential address', 'पता', 'pata']
        
        # Find column indices
        name_idx = self._find_header_index(headers, name_headers)
        dob_idx = self._find_header_index(headers, dob_headers)
        id_idx = self._find_header_index(headers, id_headers)
        address_idx = self._find_header_index(headers, address_headers)
        
        # Parse data rows
        for row in table[1:]:
            if not row or all(not cell for cell in row):
                continue
            
            voter = {}
            
            if name_idx is not None and name_idx < len(row):
                voter['name'] = str(row[name_idx]).strip() if row[name_idx] else ''
            
            if dob_idx is not None and dob_idx < len(row):
                voter['date_of_birth'] = str(row[dob_idx]).strip() if row[dob_idx] else ''
            
            if id_idx is not None and id_idx < len(row):
                voter['id_number'] = str(row[id_idx]).strip() if row[id_idx] else ''
            
            if address_idx is not None and address_idx < len(row):
                voter['address'] = str(row[address_idx]).strip() if row[address_idx] else ''
            
            # Only add if at least name or ID is present
            if voter.get('name') or voter.get('id_number'):
                voters.append(voter)
        
        return voters
    
    def _find_header_index(self, headers: List[str], possible_names: List[str]) -> Optional[int]:
        """Find the index of a header that matches any of the possible names"""
        for idx, header in enumerate(headers):
            for name in possible_names:
                if name in header:
                    return idx
        return None
    
    def parse_voter_data_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse voter data from OCR text using pattern matching
        Useful for image-based PDFs where table structure isn't preserved
        
        Args:
            text: OCR extracted text
            
        Returns:
            List of voter records
        """
        voters = []
        
        try:
            # Split text into lines
            lines = text.split('\n')
            
            # Common patterns for voter data
            # Try to find structured data patterns
            current_voter = {}
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    # Empty line might indicate end of a voter record
                    if current_voter and (current_voter.get('name') or current_voter.get('id_number')):
                        voters.append(current_voter.copy())
                        current_voter = {}
                    continue
                
                line_lower = line.lower()
                
                # Look for name patterns
                if any(keyword in line_lower for keyword in ['name', 'नाम', 'naam']):
                    # Extract name from same line or next line
                    name_match = re.search(r'[:：]\s*(.+)', line)
                    if name_match:
                        current_voter['name'] = name_match.group(1).strip()
                    elif i + 1 < len(lines):
                        current_voter['name'] = lines[i + 1].strip()
                
                # Look for DOB patterns
                elif any(keyword in line_lower for keyword in ['dob', 'date of birth', 'birth', 'जन्म']):
                    dob_match = re.search(r'[:：]\s*(.+)', line)
                    if dob_match:
                        current_voter['date_of_birth'] = dob_match.group(1).strip()
                    elif i + 1 < len(lines):
                        current_voter['date_of_birth'] = lines[i + 1].strip()
                    # Also try to find date patterns in the line
                    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
                    date_match = re.search(date_pattern, line)
                    if date_match and 'date_of_birth' not in current_voter:
                        current_voter['date_of_birth'] = date_match.group(0)
                
                # Look for ID patterns
                elif any(keyword in line_lower for keyword in ['id', 'voter id', 'epic', 'पहचान']):
                    id_match = re.search(r'[:：]\s*([A-Z0-9]+)', line, re.IGNORECASE)
                    if id_match:
                        current_voter['id_number'] = id_match.group(1).strip()
                    elif i + 1 < len(lines):
                        # Look for alphanumeric ID in next line
                        next_line = lines[i + 1].strip()
                        if re.match(r'^[A-Z0-9]+$', next_line, re.IGNORECASE):
                            current_voter['id_number'] = next_line
                
                # Look for address patterns
                elif any(keyword in line_lower for keyword in ['address', 'addr', 'पता', 'pata']):
                    addr_match = re.search(r'[:：]\s*(.+)', line)
                    if addr_match:
                        current_voter['address'] = addr_match.group(1).strip()
                    elif i + 1 < len(lines):
                        # Address might span multiple lines
                        address_lines = []
                        for j in range(i + 1, min(i + 4, len(lines))):
                            addr_line = lines[j].strip()
                            if addr_line and not any(kw in addr_line.lower() for kw in ['name', 'dob', 'id', 'voter']):
                                address_lines.append(addr_line)
                            else:
                                break
                        if address_lines:
                            current_voter['address'] = ' '.join(address_lines)
                
                # Try to detect standalone voter ID numbers (common pattern: ABC1234567)
                elif re.match(r'^[A-Z]{3}\d{7}$', line):
                    if 'id_number' not in current_voter:
                        current_voter['id_number'] = line
            
            # Add the last voter if exists
            if current_voter and (current_voter.get('name') or current_voter.get('id_number')):
                voters.append(current_voter)
            
            logger.info(f"Parsed {len(voters)} voters from OCR text")
            
        except Exception as e:
            logger.error(f"Error parsing voter data from text: {str(e)}")
        
        return voters
    
    def extract_voter_data_from_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract structured voter data from PDF
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Dictionary with extracted voter records and metadata
        """
        result = {
            'voters': [],
            'total_voters': 0,
            'pages_processed': 0,
            'tables_found': 0,
            'languages': [],
            'errors': [],
            'ocr_used': False
        }
        
        try:
            # Extract text and tables
            pdf_data = self.extract_text_from_pdf(pdf_bytes)
            result['pages_processed'] = pdf_data['total_pages']
            result['languages'] = pdf_data['languages']
            result['tables_found'] = len(pdf_data['tables'])
            
            # Parse voter data from tables
            for table_data in pdf_data['tables']:
                voters = self.parse_voter_data_from_table(table_data['data'])
                result['voters'].extend(voters)
            
            # If no voters found from text extraction, use OCR (for image-based PDFs)
            if not result['voters']:
                logger.info("No voter data found from text extraction. Attempting OCR on PDF images...")
                result['ocr_used'] = True
                
                # Determine languages for OCR
                ocr_languages = pdf_data['languages'] if pdf_data['languages'] else ['en']
                logger.info(f"Using OCR with languages: {ocr_languages}")
                
                # Perform OCR
                ocr_text = self.ocr_pdf_with_language(pdf_bytes, ocr_languages)
                result['ocr_text'] = ocr_text
                
                # Try to parse voter data from OCR text
                voters_from_ocr = self.parse_voter_data_from_text(ocr_text)
                result['voters'].extend(voters_from_ocr)
                
                logger.info(f"OCR extraction completed. Found {len(voters_from_ocr)} voters")
            
            result['total_voters'] = len(result['voters'])
            
        except Exception as e:
            logger.error(f"Error extracting voter data: {str(e)}")
            result['errors'].append(str(e))
        
        return result
    
    def process_multiple_pdfs(self, pdf_files: List[bytes]) -> Dict[str, Any]:
        """
        Process multiple PDF files and aggregate results
        
        Args:
            pdf_files: List of PDF files as bytes
            
        Returns:
            Aggregated results from all PDFs
        """
        all_voters = []
        total_pages = 0
        all_languages = set()
        errors = []
        
        for idx, pdf_bytes in enumerate(pdf_files, 1):
            try:
                logger.info(f"Processing PDF {idx}/{len(pdf_files)}")
                pdf_result = self.extract_voter_data_from_pdf(pdf_bytes)
                
                # Add source PDF info to each voter
                for voter in pdf_result['voters']:
                    voter['source_pdf'] = idx
                
                all_voters.extend(pdf_result['voters'])
                total_pages += pdf_result['pages_processed']
                all_languages.update(pdf_result['languages'])
                errors.extend(pdf_result.get('errors', []))
                
            except Exception as e:
                logger.error(f"Error processing PDF {idx}: {str(e)}")
                errors.append(f"PDF {idx}: {str(e)}")
        
        return {
            'total_voters': len(all_voters),
            'voters': all_voters,
            'total_pdfs': len(pdf_files),
            'total_pages': total_pages,
            'languages_detected': list(all_languages),
            'errors': errors
        }

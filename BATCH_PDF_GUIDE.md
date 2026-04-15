# Batch PDF Voter Analysis - Multi-Language Support

## Overview
The Voter Fraud Detection System now supports batch processing of PDF documents containing voter data in multiple languages. This feature can analyze entire voter databases from PDF files and detect fraud patterns across large datasets.

## Supported Languages

### Indian Languages
The system supports OCR and text extraction for the following languages:

- **English** (eng) - Primary language
- **Hindi** (hin) - हिन्दी
- **Bengali** (ben) - বাংলা
- **Telugu** (tel) - తెలుగు
- **Tamil** (tam) - தமிழ்
- **Marathi** (mar) - मराठी
- **Gujarati** (guj) - ગુજરાતી
- **Kannada** (kan) - ಕನ್ನಡ
- **Malayalam** (mal) - മലയാളം
- **Punjabi** (pan) - ਪੰਜਾਬੀ
- **Urdu** (urd) - اردو
- **Oriya** (ori) - ଓଡ଼ିଆ
- **Assamese** (asm) - অসমীয়া

## Installing Language Support for Tesseract

To use multi-language OCR, you need to install additional language data files for Tesseract.

### Windows Installation

1. **Download Language Data Files**
   - Visit: https://github.com/tesseract-ocr/tessdata
   - Download the `.traineddata` files for your required languages
   - For example:
     - `hin.traineddata` for Hindi
     - `ben.traineddata` for Bengali
     - `tel.traineddata` for Telugu
     - `tam.traineddata` for Tamil

2. **Install Language Files**
   - Locate your Tesseract installation directory (default: `C:\Program Files\Tesseract-OCR\`)
   - Navigate to the `tessdata` folder
   - Copy the downloaded `.traineddata` files into this folder

3. **Verify Installation**
   ```powershell
   tesseract --list-langs
   ```
   This should display all installed languages including the ones you just added.

### Alternative: Download All Languages
You can download all language files at once:
```powershell
# Navigate to tessdata directory
cd "C:\Program Files\Tesseract-OCR\tessdata"

# Download Hindi
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/hin.traineddata" -OutFile "hin.traineddata"

# Download Bengali
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/ben.traineddata" -OutFile "ben.traineddata"

# Download Tamil
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/tam.traineddata" -OutFile "tam.traineddata"

# Download Telugu
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/tel.traineddata" -OutFile "tel.traineddata"
```

## Features

### PDF Processing Capabilities

1. **Text Extraction**
   - Extracts text from native PDF documents
   - Preserves table structures
   - Detects language automatically

2. **Table Parsing**
   - Identifies voter data tables
   - Extracts structured information:
     - Name (Name/Voter Name/Full Name)
     - Date of Birth (DoB/Date of Birth)
     - ID Number (ID/Voter ID/EPIC No)
     - Address (Address/Residential Address)
   - Supports multi-language column headers

3. **OCR Processing**
   - For image-based PDFs or scanned documents
   - Multi-language OCR with auto-detection
   - High-resolution image extraction (300 DPI)

4. **Batch Processing**
   - Process multiple PDF files simultaneously
   - Aggregate results across all documents
   - Track source PDF for each voter entry

### Fraud Detection Features

For each voter entry extracted from PDFs, the system performs:

1. **Duplicate Detection**
   - Name matching (fuzzy matching for variations)
   - Date of birth comparison
   - ID number validation
   - Address similarity checking
   - Cross-PDF duplicate detection

2. **Data Validation**
   - Missing field detection
   - Format validation
   - Consistency checks

3. **Risk Scoring**
   - Automatic risk level assignment (LOW/MEDIUM/HIGH)
   - Fraud probability calculation
   - Flag generation for suspicious entries

## Usage

### Web Interface

1. **Access the Batch Analysis Page**
   - Navigate to: `http://localhost:8000/static/batch_analysis.html`
   - Or click "Batch PDF Analysis" from the main page

2. **Upload PDF Files**
   - Drag and drop PDF files onto the upload area
   - Or click "Select PDF Files" to browse
   - You can upload multiple PDFs at once

3. **Analyze**
   - Click "Analyze All PDFs" button
   - Wait for processing to complete (may take several minutes for large files)

4. **Review Results**
   - View summary statistics
   - Filter voters by risk level
   - Expand individual entries for details
   - Export results as JSON

### API Endpoint

```python
POST /analyze-pdf-batch
Content-Type: multipart/form-data

files: List of PDF files
```

**Response:**
```json
{
  "success": true,
  "extraction": {
    "total_pdfs": 3,
    "total_pages": 45,
    "languages_detected": ["en", "hi"],
    "extraction_errors": []
  },
  "analysis": {
    "fraud_summary": {
      "total_voters": 150,
      "flagged_voters": 12,
      "high_risk": 3,
      "medium_risk": 9,
      "low_risk": 138,
      "duplicate_count": 8
    },
    "flagged_percentage": 8.0,
    "analyzed_voters": [...]
  },
  "database_stats": {
    "total_voters": 150,
    "next_id": 151
  }
}
```

## PDF Format Requirements

### Recommended PDF Structure

For best results, your PDF should contain voter data in table format with clear headers:

| Name | Date of Birth | ID Number | Address |
|------|---------------|-----------|---------|
| John Doe | 01/01/1990 | VID123456 | 123 Main St |
| Jane Smith | 15/05/1985 | VID789012 | 456 Oak Ave |

### Supported Column Names

The system recognizes various column header formats:

**Name columns:**
- Name, Voter Name, Full Name
- नाम (Hindi), Naam

**Date of Birth columns:**
- DoB, Date of Birth, Birth Date
- जन्म तिथि (Hindi), Janma Tithi

**ID Number columns:**
- ID, Voter ID, EPIC No, ID Number
- पहचान संख्या (Hindi)

**Address columns:**
- Address, Residential Address
- पता (Hindi), Pata

## Example Use Cases

### 1. Analyzing Voter Database from Election Commission

```python
# Upload PDF files containing voter rolls
# System will:
# - Extract all voter information
# - Detect duplicates across all PDFs
# - Flag suspicious entries
# - Generate comprehensive report
```

### 2. Multi-Language Voter Data

```python
# PDFs with Hindi and English mixed content
# System automatically:
# - Detects languages used
# - Applies appropriate OCR models
# - Parses data correctly
# - Reports language distribution
```

### 3. Cross-Reference Multiple Districts

```python
# Upload voter data from different districts
# System identifies:
# - Same person registered in multiple districts
# - Duplicate ID numbers
# - Address inconsistencies
# - Potential fraud patterns
```

## Performance Considerations

### Processing Time
- Small PDFs (< 10 pages): ~30 seconds per file
- Medium PDFs (10-50 pages): ~2-5 minutes per file
- Large PDFs (> 50 pages): ~5-15 minutes per file

### Optimization Tips
1. Use native PDF text when possible (faster than OCR)
2. Ensure good quality scans (300 DPI or higher)
3. Split very large PDFs into smaller chunks
4. Use clear table structures in PDFs

## Troubleshooting

### Issue: Languages Not Detected
**Solution:** Install the required Tesseract language data files (see installation instructions above)

### Issue: Poor OCR Accuracy
**Solution:** 
- Ensure PDF images are high resolution
- Check that correct language files are installed
- Verify Tesseract can access the language files

### Issue: Tables Not Recognized
**Solution:**
- Ensure tables have clear borders
- Check column headers match supported formats
- Try using PDFs with actual table structures (not images of tables)

### Issue: Slow Processing
**Solution:**
- Process fewer PDFs at once
- Reduce PDF file sizes
- Use native PDF text instead of scanned images

## Technical Architecture

### Components

1. **PDFProcessor** (`pdf_processor.py`)
   - PDF text extraction using pdfplumber
   - Image extraction for OCR
   - Table parsing and voter data extraction
   - Language detection

2. **Multi-Language OCR**
   - pytesseract with language support
   - Automatic language detection with langdetect
   - Fallback to English if detection fails

3. **Batch Analysis Endpoint** (`/analyze-pdf-batch`)
   - File upload handling
   - PDF processing coordination
   - Fraud detection per voter
   - Result aggregation

4. **Web Interface** (`batch_analysis.html`)
   - Drag-and-drop file upload
   - Real-time progress indication
   - Interactive results display
   - Export functionality

## Future Enhancements

Planned features for upcoming releases:

1. **Advanced Pattern Detection**
   - Machine learning-based fraud prediction
   - Behavioral pattern analysis
   - Network analysis of related voters

2. **Additional Language Support**
   - More regional languages
   - International language support
   - Custom language training

3. **Enhanced PDF Processing**
   - Support for complex PDF layouts
   - Better handling of forms
   - Signature verification

4. **Database Integration**
   - PostgreSQL/MySQL support
   - Data persistence
   - Historical analysis

5. **Report Generation**
   - PDF report export
   - Excel/CSV export
   - Visualization dashboards

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the Tesseract documentation: https://tesseract-ocr.github.io/
3. Verify language files are properly installed
4. Check system logs for detailed error messages

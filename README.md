# Fake Voter Entry Detection System

🔍 An AI-powered web application for detecting fraudulent voter registrations using OCR, face recognition, and machine learning anomaly detection.

## Features

- **OCR Text Extraction**: Extracts text from voter ID cards and address proof documents using Tesseract OCR
- **Face Recognition**: Detects duplicate faces across voter entries using face_recognition library
- **Age Verification**: Estimates age from facial features using DeepFace and compares with date of birth
- **Fuzzy Matching**: Validates consistency between documents using Levenshtein distance
- **Anomaly Detection**: Identifies outliers in voter data using scikit-learn's IsolationForest
- **Risk Scoring**: Provides comprehensive fraud risk assessment with detailed flags

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **OCR**: pytesseract + OpenCV
- **Face Recognition**: face_recognition (dlib-based)
- **Age Estimation**: DeepFace
- **ML**: scikit-learn (IsolationForest, LocalOutlierFactor)
- **Server**: Uvicorn (ASGI)

### Frontend
- **HTML5/CSS3/JavaScript**: Responsive single-page application
- **Modern UI**: Gradient design with real-time feedback

## Installation

### Prerequisites

1. **Python 3.8+** installed
2. **Tesseract OCR** installed:
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - Mac: `brew install tesseract`

3. **CMake** (for dlib):
   - Windows: Download from https://cmake.org/download/
   - Linux: `sudo apt-get install cmake`
   - Mac: `brew install cmake`

### Setup Steps

1. **Clone the repository**:
```bash
git clone <repository-url>
cd "Voter Ai"
```

2. **Create virtual environment**:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Note: Installing `dlib` and `face_recognition` may take several minutes as they compile from source.

4. **Configure environment**:
```bash
# Copy example environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env and set TESSERACT_CMD path if needed
```

5. **Run the application**:
```bash
python main.py
```

The application will be available at `http://localhost:8000`

## Usage

1. **Open the web interface** at `http://localhost:8000/static/index.html`

2. **Upload documents**:
   - Voter ID Card image
   - Address Proof document image
   - Face photograph

3. **Click "Analyze for Fraud Detection"**

4. **Review results**:
   - Risk level (LOW/MEDIUM/HIGH)
   - Extracted information from documents
   - Document consistency checks
   - Face verification results
   - Anomaly detection findings
   - Detailed risk flags

## API Documentation

### Endpoints

#### `POST /analyze`
Main analysis endpoint for voter entry verification.

**Request**: multipart/form-data
- `voter_id_image`: Image file
- `address_proof_image`: Image file
- `face_photo`: Image file

**Response**: JSON
```json
{
  "success": true,
  "data": {
    "risk_score": 15.5,
    "risk_level": "LOW",
    "extracted_text": {...},
    "fuzzy_match": {...},
    "duplicate_face": {...},
    "age_check": {...},
    "anomalies": {...},
    "fraud_risk_flags": {...}
  }
}
```

#### `GET /health`
Health check endpoint.

#### `POST /reset-database`
Reset in-memory face database (testing only).

#### `GET /docs`
Interactive API documentation (Swagger UI).

## Docker Deployment

### Build Docker image:
```bash
docker build -t voter-fraud-detection .
```

### Run container:
```bash
docker run -p 8000:8000 voter-fraud-detection
```

## Heroku Deployment

1. **Install Heroku CLI**

2. **Login to Heroku**:
```bash
heroku login
```

3. **Create Heroku app**:
```bash
heroku create your-app-name
```

4. **Add buildpacks**:
```bash
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
heroku buildpacks:add --index 2 heroku/python
```

5. **Create Aptfile** (for Tesseract):
```bash
echo "tesseract-ocr
tesseract-ocr-eng
libsm6
libxext6
libxrender-dev" > Aptfile
```

6. **Deploy**:
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku master
```

## Configuration

Edit `.env` file to customize:

```env
# Application
PORT=8000
DEBUG=True

# OCR
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe

# Detection Thresholds
FUZZY_MATCH_THRESHOLD=0.8
AGE_MISMATCH_THRESHOLD=5
ANOMALY_CONTAMINATION=0.01
FACE_MATCH_TOLERANCE=0.6
```

## Project Structure

```
Voter Ai/
├── main.py                 # FastAPI application
├── ocr_processor.py        # OCR text extraction module
├── face_analyzer.py        # Face recognition & age estimation
├── validators.py           # Fuzzy matching & anomaly detection
├── requirements.txt        # Python dependencies
├── Procfile               # Heroku deployment config
├── Dockerfile             # Docker containerization
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore patterns
├── static/
│   └── index.html         # Frontend web interface
└── README.md              # This file
```

## Key Components

### OCR Processing (`ocr_processor.py`)
- Image preprocessing (grayscale, thresholding)
- Text extraction using Tesseract
- Parsing voter ID and address proof fields
- Date normalization

### Face Analysis (`face_analyzer.py`)
- Face encoding using dlib (128-dimension vectors)
- Duplicate detection via face comparison
- Age prediction using DeepFace models
- Face quality assessment

### Data Validation (`validators.py`)
- Fuzzy string matching (SequenceMatcher)
- Age calculation from date of birth
- Anomaly detection (IsolationForest)
- Data completeness checks
- Batch duplicate detection

## Performance Considerations

- **Face encoding**: ~1-2 seconds per image
- **OCR extraction**: ~2-3 seconds per document
- **Age prediction**: ~3-5 seconds (first call loads model)
- **Total analysis**: ~10-15 seconds per entry

For production:
- Implement caching for face encodings
- Use database instead of in-memory storage
- Consider batch processing for multiple entries
- Optimize image sizes before processing

## Troubleshooting

### Tesseract not found
Ensure Tesseract is installed and `TESSERACT_CMD` in `.env` points to correct path.

### dlib installation fails
Install CMake and Visual Studio Build Tools (Windows) or build-essential (Linux).

### DeepFace model download
First run downloads models (~100MB). Ensure internet connection.

### Face not detected
Ensure face photo has good lighting and face is clearly visible.

## Security Notes

- This is a demonstration application
- In production, implement:
  - Authentication and authorization
  - Rate limiting
  - Input validation and sanitization
  - Secure file storage
  - Database encryption
  - HTTPS/SSL
  - Audit logging

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions, please open an issue on GitHub.

## Acknowledgments

- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- face_recognition: https://github.com/ageitgey/face_recognition
- DeepFace: https://github.com/serengil/deepface
- FastAPI: https://fastapi.tiangolo.com/
- scikit-learn: https://scikit-learn.org/

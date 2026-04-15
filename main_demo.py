"""
Test/Demo version of the Voter Fraud Detection app
This version works without Tesseract OCR and face recognition libraries
Useful for testing the web interface and basic structure
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Fake Voter Entry Detection System (Demo)",
    description="Demo version - install full dependencies for complete functionality",
    version="1.0.0-demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to frontend"""
    return """
    <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/static/index.html">
        </head>
        <body>
            <p>Redirecting to application...</p>
        </body>
    </html>
    """


@app.post("/analyze")
async def analyze_voter_entry(
    voter_id_image: UploadFile = File(...),
    address_proof_image: UploadFile = File(...),
    face_photo: UploadFile = File(...)
) -> JSONResponse:
    """
    Demo analysis endpoint - simulates fraud detection
    Install pytesseract, face_recognition, and deepface for full functionality
    """
    try:
        # Read uploaded files
        id_bytes = await voter_id_image.read()
        addr_bytes = await address_proof_image.read()
        face_bytes = await face_photo.read()
        
        # Decode images
        np_arr_id = np.frombuffer(id_bytes, np.uint8)
        np_arr_addr = np.frombuffer(addr_bytes, np.uint8)
        np_arr_face = np.frombuffer(face_bytes, np.uint8)
        
        img_id = cv2.imdecode(np_arr_id, cv2.IMREAD_COLOR)
        img_addr = cv2.imdecode(np_arr_addr, cv2.IMREAD_COLOR)
        img_face = cv2.imdecode(np_arr_face, cv2.IMREAD_COLOR)
        
        if img_id is None or img_addr is None or img_face is None:
            raise HTTPException(status_code=400, detail="Failed to decode images")
        
        # DEMO MODE - Return simulated results
        results = {
            "extracted_text": {
                "voter_id": {
                    "raw_text": "DEMO MODE: Install pytesseract for real OCR",
                    "parsed_fields": {
                        "name": "John Doe (Demo)",
                        "date_of_birth": "01/01/1990",
                        "id_number": "ABC1234567",
                        "address": "123 Demo Street, Demo City"
                    }
                },
                "address_proof": {
                    "raw_text": "DEMO MODE: Install pytesseract for real OCR",
                    "parsed_fields": {
                        "name": "John Doe (Demo)",
                        "address": "123 Demo Street, Demo City"
                    }
                }
            },
            "fuzzy_match": {
                "name_similarity": 0.95,
                "address_similarity": 0.92,
                "overall_consistency": 0.93
            },
            "duplicate_face": {
                "is_duplicate": False,
                "matched_id": None
            },
            "age_check": {
                "predicted_age": 34,
                "age_from_dob": 35,
                "age_mismatch_flag": False,
                "age_difference": 1
            },
            "anomalies": {
                "is_anomaly": False,
                "anomaly_score": 0.15,
                "details": {}
            },
            "fraud_risk_flags": {
                "fuzzy_name_issue": False,
                "fuzzy_address_issue": False,
                "face_duplicate_issue": False,
                "age_mismatch_issue": False,
                "anomaly_detected": False,
                "missing_fields": False
            },
            "risk_score": 8.5,
            "risk_level": "LOW",
            "demo_mode": True,
            "message": "DEMO MODE: Install full dependencies for real analysis"
        }
        
        return JSONResponse(content={
            "success": True,
            "data": results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy (demo mode)",
        "message": "Install pytesseract, face_recognition, and deepface for full functionality"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("🚀 Starting Voter Fraud Detection System (DEMO MODE)")
    print("=" * 60)
    print(f"📍 Server: http://localhost:{port}")
    print(f"🌐 Web UI: http://localhost:{port}/static/index.html")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print("=" * 60)
    print("⚠️  DEMO MODE - Showing sample data")
    print("📦 To enable full functionality, install:")
    print("   1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   2. Run: pip install pytesseract face-recognition deepface")
    print("=" * 60)
    
    uvicorn.run(
        "main_demo:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

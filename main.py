"""
Main FastAPI application for Fake Voter Entry Detection
Handles file uploads and orchestrates the analysis pipeline
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
from typing import Dict, Any
import os
from dotenv import load_dotenv

from ocr_processor import OCRProcessor
try:
    from face_analyzer import FaceAnalyzer
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️  Warning: face_recognition not available. Face analysis features disabled.")
from validators import DataValidator
from duplicate_detector import DuplicateDetector
from pdf_processor import PDFProcessor
from pdf_processor import PDFProcessor

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Fake Voter Entry Detection System",
    description="AI-powered system to detect fraudulent voter registrations using OCR, face recognition, and anomaly detection",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize processors
ocr_processor = OCRProcessor()
face_analyzer = FaceAnalyzer() if FACE_RECOGNITION_AVAILABLE else None
data_validator = DataValidator()
duplicate_detector = DuplicateDetector()
pdf_processor = PDFProcessor()

# In-memory storage for known face encodings (replace with database in production)
known_face_encodings = []
known_face_ids = []


@app.get("/")
async def root():
    """Root endpoint - redirects to frontend"""
    return {"message": "Fake Voter Entry Detection API", "docs": "/docs"}


@app.post("/analyze")
async def analyze_voter_entry(
    voter_id_image: UploadFile = File(..., description="Voter ID card image"),
    address_proof_image: UploadFile = File(..., description="Address proof document image"),
    face_photo: UploadFile = File(..., description="Face photograph for verification")
) -> JSONResponse:
    """
    Main analysis endpoint that processes uploaded images and detects potential fraud
    
    Steps:
    1. Read and decode uploaded images
    2. Extract text using OCR from ID and address proof
    3. Parse extracted text for structured fields (name, DoB, address)
    4. Perform fuzzy matching between documents
    5. Analyze face for duplicates and age estimation
    6. Run anomaly detection on structured data
    7. Compile risk flags and return results
    """
    try:
        # Step 1: Read uploaded files into memory
        id_bytes = await voter_id_image.read()
        addr_bytes = await address_proof_image.read()
        face_bytes = await face_photo.read()
        
        # Convert bytes to numpy arrays for OpenCV
        np_arr_id = np.frombuffer(id_bytes, np.uint8)
        np_arr_addr = np.frombuffer(addr_bytes, np.uint8)
        np_arr_face = np.frombuffer(face_bytes, np.uint8)
        
        # Decode images using OpenCV
        img_id = cv2.imdecode(np_arr_id, cv2.IMREAD_COLOR)
        img_addr = cv2.imdecode(np_arr_addr, cv2.IMREAD_COLOR)
        img_face = cv2.imdecode(np_arr_face, cv2.IMREAD_COLOR)
        
        # Validate images were decoded successfully
        if img_id is None or img_addr is None or img_face is None:
            raise HTTPException(status_code=400, detail="Failed to decode one or more images")
        
        results: Dict[str, Any] = {}
        
        # Step 2: OCR Text Extraction from ID card and address proof
        # Preprocess images (grayscale, thresholding) for better OCR accuracy
        text_id = ocr_processor.extract_text(img_id)
        text_addr = ocr_processor.extract_text(img_addr)
        
        # Step 3: Parse extracted text to find structured fields
        parsed_id = ocr_processor.parse_voter_id(text_id)
        parsed_addr = ocr_processor.parse_address_proof(text_addr)
        
        results["extracted_text"] = {
            "voter_id": {
                "raw_text": text_id[:500],  # Truncate for response size
                "parsed_fields": parsed_id
            },
            "address_proof": {
                "raw_text": text_addr[:500],
                "parsed_fields": parsed_addr
            }
        }
        
        # Step 4: Fuzzy Matching for consistency checks
        # Compare name and address fields between documents
        fuzzy_results = data_validator.fuzzy_match_fields(parsed_id, parsed_addr)
        results["fuzzy_match"] = fuzzy_results
        
        # Step 5: Face Recognition for duplicate detection
        # Encode face from uploaded photo and compare with known faces
        face_encoding = None
        duplicate_found = False
        duplicate_id = None
        predicted_age = None
        
        if FACE_RECOGNITION_AVAILABLE and face_analyzer:
            face_encoding = face_analyzer.encode_face(img_face)
            
            if face_encoding is not None and known_face_encodings:
                duplicate_found, duplicate_id = face_analyzer.find_duplicate(
                    face_encoding, 
                    known_face_encodings, 
                    known_face_ids
                )
            
            # Step 6: Predict age from face and compare with DoB
            predicted_age = face_analyzer.predict_age(img_face)
            
            # Store this encoding for future comparisons (in production, save to database)
            if face_encoding is not None:
                known_face_encodings.append(face_encoding)
                known_face_ids.append(len(known_face_encodings))  # Simple ID assignment
        
        results["duplicate_face"] = {
            "is_duplicate": duplicate_found,
            "matched_id": duplicate_id,
            "feature_available": FACE_RECOGNITION_AVAILABLE
        }
        
        age_from_dob = None
        if parsed_id.get("date_of_birth"):
            age_from_dob = data_validator.calculate_age(parsed_id["date_of_birth"])
        
        age_mismatch = False
        if predicted_age is not None and age_from_dob is not None:
            age_difference = abs(predicted_age - age_from_dob)
            age_mismatch = age_difference > int(os.getenv("AGE_MISMATCH_THRESHOLD", 5))
        
        results["age_check"] = {
            "predicted_age": predicted_age,
            "age_from_dob": age_from_dob,
            "age_mismatch_flag": age_mismatch,
            "age_difference": abs(predicted_age - age_from_dob) if predicted_age and age_from_dob else None
        }
        
        # Step 7: Structured anomaly detection using machine learning
        # Detect outliers in birth year, name patterns, etc.
        anomaly_results = data_validator.detect_anomalies(parsed_id, age_from_dob)
        results["anomalies"] = anomaly_results
        
        # Step 8: COMPREHENSIVE DUPLICATE DETECTION
        # Check for duplicates across all fields (name, DoB, ID, address, face)
        # Prepare voter data for duplicate checking
        face_hash = duplicate_detector.hash_image(face_bytes) if face_bytes else None
        
        voter_data_for_check = {
            "name": parsed_id.get("name") or parsed_addr.get("name"),
            "date_of_birth": parsed_id.get("date_of_birth"),
            "id_number": parsed_id.get("id_number"),
            "address": parsed_id.get("address") or parsed_addr.get("address"),
            "face_hash": face_hash
        }
        
        # Check for duplicates before adding to database
        duplicate_results = duplicate_detector.check_duplicates(voter_data_for_check)
        results["duplicate_detection"] = duplicate_results
        
        # Add this voter to the database for future comparisons
        if not duplicate_results["has_duplicates"] or True:  # Add even if duplicate for tracking
            voter_id = duplicate_detector.add_voter(voter_data_for_check)
            results["voter_id"] = voter_id
        
        # Get database statistics
        db_stats = duplicate_detector.get_statistics()
        results["database_stats"] = db_stats
        
        # Step 9: Compile fraud risk flags
        # Summarize all checks and flag potential issues
        flags = {
            "fuzzy_name_issue": fuzzy_results["name_similarity"] < float(os.getenv("FUZZY_MATCH_THRESHOLD", 0.8)),
            "fuzzy_address_issue": fuzzy_results["address_similarity"] < float(os.getenv("FUZZY_MATCH_THRESHOLD", 0.8)),
            "face_duplicate_issue": duplicate_found,
            "age_mismatch_issue": age_mismatch,
            "anomaly_detected": anomaly_results.get("is_anomaly", False),
            "missing_fields": not all([
                parsed_id.get("name"),
                parsed_id.get("date_of_birth"),
                parsed_addr.get("address")
            ]),
            "duplicate_name_found": len(duplicate_results["field_duplicates"]["name"]) > 0,
            "duplicate_dob_found": len(duplicate_results["field_duplicates"]["date_of_birth"]) > 0,
            "duplicate_id_found": len(duplicate_results["field_duplicates"]["id_number"]) > 0,
            "duplicate_address_found": len(duplicate_results["field_duplicates"]["address"]) > 0,
            "duplicate_face_found": len(duplicate_results["field_duplicates"]["face_hash"]) > 0,
            "multiple_field_duplicates": len(duplicate_results["exact_matches"]) > 0
        }
        
        # Calculate overall risk score (0-100)
        risk_score = (
            sum(flags.values()) * (100 / len(flags))
        )
        
        # Add duplicate risk score
        risk_score = (risk_score + duplicate_results["duplicate_risk_score"]) / 2
        
        results["fraud_risk_flags"] = flags
        results["risk_score"] = round(risk_score, 2)
        results["risk_level"] = (
            "HIGH" if risk_score >= 60 else
            "MEDIUM" if risk_score >= 30 else
            "LOW"
        )
        
        return JSONResponse(content={
            "success": True,
            "data": results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/reset-database")
async def reset_face_database():
    """Reset the in-memory face database and voter database (for testing purposes)"""
    global known_face_encodings, known_face_ids
    known_face_encodings = []
    known_face_ids = []
    duplicate_detector.clear_database()
    return {
        "message": "All databases reset successfully",
        "voters_cleared": True,
        "faces_cleared": True
    }


@app.get("/database-stats")
async def get_database_stats():
    """Get current database statistics"""
    stats = duplicate_detector.get_statistics()
    return {
        "total_voters_registered": stats["total_voters"],
        "next_voter_id": stats["next_id"]
    }


@app.post("/analyze-pdf-batch")
async def analyze_pdf_batch(files: list[UploadFile] = File(...)):
    """
    Analyze multiple PDF files containing voter data
    Extracts voter information and performs fraud detection on each entry
    
    Args:
        files: List of PDF files to analyze
        
    Returns:
        Comprehensive analysis results with fraud detection for all voters
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Read all PDF files
        pdf_files = []
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            pdf_bytes = await file.read()
            pdf_files.append(pdf_bytes)
        
        # Extract voter data from all PDFs
        extraction_result = pdf_processor.process_multiple_pdfs(pdf_files)
        
        # Perform fraud detection on each voter
        analyzed_voters = []
        fraud_summary = {
            'total_voters': extraction_result['total_voters'],
            'flagged_voters': 0,
            'high_risk': 0,
            'medium_risk': 0,
            'low_risk': 0,
            'duplicate_count': 0
        }
        
        for idx, voter in enumerate(extraction_result['voters']):
            # Check for duplicates
            duplicate_check = duplicate_detector.check_duplicates(voter)
            
            # Validate data
            validation_flags = {
                'missing_fields': not all([
                    voter.get('name'),
                    voter.get('date_of_birth'),
                    voter.get('id_number')
                ]),
                'duplicate_name_found': 'name' in duplicate_check.get('field_duplicates', {}),
                'duplicate_dob_found': 'date_of_birth' in duplicate_check.get('field_duplicates', {}),
                'duplicate_id_found': 'id_number' in duplicate_check.get('field_duplicates', {}),
                'duplicate_address_found': 'address' in duplicate_check.get('field_duplicates', {}),
            }
            
            # Calculate risk score
            risk_score = 0.0
            if validation_flags['missing_fields']:
                risk_score += 30
            if duplicate_check['has_duplicates']:
                risk_score += 40
            if duplicate_check['exact_matches']:
                risk_score += 60
            
            risk_score = min(risk_score, 100)
            
            # Determine risk level
            if risk_score >= 70:
                risk_level = 'HIGH'
                fraud_summary['high_risk'] += 1
            elif risk_score >= 40:
                risk_level = 'MEDIUM'
                fraud_summary['medium_risk'] += 1
            else:
                risk_level = 'LOW'
                fraud_summary['low_risk'] += 1
            
            if risk_score >= 40:
                fraud_summary['flagged_voters'] += 1
            
            if duplicate_check['has_duplicates']:
                fraud_summary['duplicate_count'] += 1
            
            analyzed_voter = {
                'voter_id': idx + 1,
                'source_pdf': voter.get('source_pdf', 'unknown'),
                'data': voter,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'flags': validation_flags,
                'duplicate_info': duplicate_check,
                'flagged': risk_score >= 40
            }
            
            analyzed_voters.append(analyzed_voter)
            
            # Add to database if low risk and no exact duplicates
            if risk_score < 40 and not duplicate_check['exact_matches']:
                duplicate_detector.add_voter(voter)
        
        return {
            "success": True,
            "extraction": {
                "total_pdfs": extraction_result['total_pdfs'],
                "total_pages": extraction_result['total_pages'],
                "languages_detected": extraction_result['languages_detected'],
                "extraction_errors": extraction_result.get('errors', [])
            },
            "analysis": {
                "fraud_summary": fraud_summary,
                "flagged_percentage": round((fraud_summary['flagged_voters'] / fraud_summary['total_voters'] * 100), 2) if fraud_summary['total_voters'] > 0 else 0,
                "analyzed_voters": analyzed_voters
            },
            "database_stats": duplicate_detector.get_statistics()
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing PDFs: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "ocr": "operational",
            "face_recognition": "operational" if FACE_RECOGNITION_AVAILABLE else "disabled",
            "anomaly_detection": "operational"
        }
    }
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=debug
    )

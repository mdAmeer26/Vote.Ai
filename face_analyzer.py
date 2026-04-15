"""
Face Analysis Module
Uses face_recognition (dlib) and DeepFace for:
- Face encoding and matching (duplicate detection)
- Age estimation from facial features
"""
import face_recognition
import cv2
import numpy as np
from typing import Optional, Tuple, List
import os
from deepface import DeepFace


class FaceAnalyzer:
    """Handles face recognition and age estimation tasks"""
    
    def __init__(self):
        """Initialize face analyzer with configuration"""
        self.tolerance = float(os.getenv("FACE_MATCH_TOLERANCE", 0.6))
    
    def encode_face(self, image) -> Optional[np.ndarray]:
        """
        Encode face from image using face_recognition library
        Returns 128-dimensional face encoding vector
        """
        try:
            # Convert BGR (OpenCV) to RGB (face_recognition)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find all faces in the image
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                print("No face detected in image")
                return None
            
            # Get face encodings (use first face if multiple detected)
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if face_encodings:
                return face_encodings[0]
            
            return None
            
        except Exception as e:
            print(f"Face encoding error: {str(e)}")
            return None
    
    def find_duplicate(
        self, 
        face_encoding: np.ndarray,
        known_encodings: List[np.ndarray],
        known_ids: List[int]
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if face encoding matches any known face encodings
        Returns (is_duplicate, matched_id)
        
        Uses face_recognition.compare_faces with distance threshold
        Lower tolerance = stricter matching (default 0.6)
        """
        try:
            if not known_encodings:
                return False, None
            
            # Compare face against all known faces
            matches = face_recognition.compare_faces(
                known_encodings,
                face_encoding,
                tolerance=self.tolerance
            )
            
            # Calculate face distances (lower = more similar)
            face_distances = face_recognition.face_distance(
                known_encodings,
                face_encoding
            )
            
            # Find best match
            if True in matches:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    return True, known_ids[best_match_index]
            
            return False, None
            
        except Exception as e:
            print(f"Face duplicate detection error: {str(e)}")
            return False, None
    
    def predict_age(self, image) -> Optional[int]:
        """
        Predict age from face image using DeepFace
        DeepFace uses pre-trained deep learning models for age estimation
        Returns predicted age in years
        """
        try:
            # DeepFace expects RGB format
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Analyze face for age
            # enforce_detection=False allows analysis even if face detection is uncertain
            analysis = DeepFace.analyze(
                img_path=rgb_image,
                actions=['age'],
                enforce_detection=False,
                silent=True
            )
            
            # DeepFace may return list or dict depending on version
            if isinstance(analysis, list):
                analysis = analysis[0]
            
            predicted_age = int(analysis.get('age', 0))
            
            return predicted_age if predicted_age > 0 else None
            
        except Exception as e:
            print(f"Age prediction error: {str(e)}")
            return None
    
    def analyze_face_quality(self, image) -> dict:
        """
        Analyze face image quality metrics:
        - Face detection confidence
        - Image brightness
        - Image blur detection
        Returns quality metrics for validation
        """
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_image)
            
            # Calculate brightness
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Calculate blur (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            quality = {
                "face_detected": len(face_locations) > 0,
                "num_faces": len(face_locations),
                "brightness": float(brightness),
                "sharpness": float(laplacian_var),
                "is_blurry": laplacian_var < 100,  # Threshold for blur
                "is_too_dark": brightness < 50,
                "is_too_bright": brightness > 200
            }
            
            return quality
            
        except Exception as e:
            print(f"Face quality analysis error: {str(e)}")
            return {
                "face_detected": False,
                "error": str(e)
            }
    
    def compare_faces_similarity(
        self,
        encoding1: np.ndarray,
        encoding2: np.ndarray
    ) -> float:
        """
        Calculate similarity score between two face encodings
        Returns value between 0 (completely different) and 1 (identical)
        """
        try:
            # Calculate Euclidean distance
            distance = np.linalg.norm(encoding1 - encoding2)
            
            # Convert distance to similarity score (0-1 range)
            # Distance of 0 = similarity 1.0, distance of 1 = similarity 0
            similarity = max(0, 1 - distance)
            
            return float(similarity)
            
        except Exception as e:
            print(f"Face similarity calculation error: {str(e)}")
            return 0.0
    
    def extract_face_region(self, image) -> Optional[np.ndarray]:
        """
        Extract and return just the face region from image
        Useful for focused analysis
        """
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                return None
            
            # Get first face location (top, right, bottom, left)
            top, right, bottom, left = face_locations[0]
            
            # Extract face region with some padding
            padding = 20
            face_image = image[
                max(0, top-padding):bottom+padding,
                max(0, left-padding):right+padding
            ]
            
            return face_image
            
        except Exception as e:
            print(f"Face extraction error: {str(e)}")
            return None

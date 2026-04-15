"""
Data Validation Module
Handles fuzzy matching, anomaly detection, and data consistency checks
"""
from difflib import SequenceMatcher
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import os
import re


class DataValidator:
    """Validates data consistency and detects anomalies"""
    
    def __init__(self):
        """Initialize validator with configuration"""
        self.fuzzy_threshold = float(os.getenv("FUZZY_MATCH_THRESHOLD", 0.8))
        self.contamination = float(os.getenv("ANOMALY_CONTAMINATION", 0.01))
        
        # Training data for anomaly detection (in production, load from database)
        # Sample birth years for normal distribution
        self.training_birth_years = []
        self.training_features = []
        
        # Initialize with some reasonable defaults (ages 18-100 for voters)
        current_year = datetime.now().year
        self.training_birth_years = list(range(current_year - 100, current_year - 18))
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity score between two strings using SequenceMatcher
        Returns value between 0 (completely different) and 1 (identical)
        Uses Levenshtein distance-like algorithm for fuzzy matching
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize strings (lowercase, strip whitespace)
        text1_norm = text1.lower().strip()
        text2_norm = text2.lower().strip()
        
        # Calculate similarity ratio
        similarity = SequenceMatcher(None, text1_norm, text2_norm).ratio()
        
        return float(similarity)
    
    def fuzzy_match_fields(
        self,
        parsed_id: Dict[str, Optional[str]],
        parsed_addr: Dict[str, Optional[str]]
    ) -> Dict[str, float]:
        """
        Perform fuzzy matching between fields from ID and address proof
        Compares name and address fields
        Returns similarity scores (0-1)
        """
        results = {
            "name_similarity": 0.0,
            "address_similarity": 0.0,
            "overall_consistency": 0.0
        }
        
        # Compare names
        name_id = parsed_id.get("name", "")
        name_addr = parsed_addr.get("name", "")
        
        if name_id and name_addr:
            results["name_similarity"] = self.calculate_similarity(name_id, name_addr)
        
        # Compare addresses
        addr_id = parsed_id.get("address", "")
        addr_proof = parsed_addr.get("address", "")
        
        if addr_id and addr_proof:
            results["address_similarity"] = self.calculate_similarity(addr_id, addr_proof)
        
        # Calculate overall consistency (average of available comparisons)
        scores = [s for s in [results["name_similarity"], results["address_similarity"]] if s > 0]
        if scores:
            results["overall_consistency"] = sum(scores) / len(scores)
        
        return results
    
    def calculate_age(self, date_string: str) -> Optional[int]:
        """
        Calculate age from date of birth string
        Handles various date formats
        """
        if not date_string:
            return None
        
        # Common date formats
        date_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%Y/%m/%d"
        ]
        
        birth_date = None
        for fmt in date_formats:
            try:
                birth_date = datetime.strptime(date_string, fmt)
                break
            except ValueError:
                continue
        
        if not birth_date:
            # Try extracting year from string if full date parsing fails
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', date_string)
            if year_match:
                birth_year = int(year_match.group(1))
                current_year = datetime.now().year
                return current_year - birth_year
            return None
        
        # Calculate age
        today = datetime.now()
        age = today.year - birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    def detect_anomalies(
        self,
        parsed_data: Dict[str, Optional[str]],
        age: Optional[int]
    ) -> Dict[str, any]:
        """
        Detect anomalies using machine learning (IsolationForest)
        Checks for outliers in:
        - Birth year
        - Age distribution
        - Name patterns (unusual characters, length)
        Returns anomaly flags and scores
        """
        results = {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "details": {}
        }
        
        try:
            features_to_check = []
            
            # Check age/birth year anomaly
            if age is not None:
                current_year = datetime.now().year
                birth_year = current_year - age
                
                # Check if age is within valid voter range (18-120)
                if age < 18 or age > 120:
                    results["details"]["invalid_age"] = True
                    results["is_anomaly"] = True
                
                # Use IsolationForest for outlier detection
                if self.training_birth_years:
                    # Prepare training data
                    X_train = np.array(self.training_birth_years).reshape(-1, 1)
                    
                    # Fit model
                    iso_forest = IsolationForest(
                        contamination=self.contamination,
                        random_state=42
                    )
                    iso_forest.fit(X_train)
                    
                    # Predict if current birth year is an outlier
                    prediction = iso_forest.predict([[birth_year]])
                    anomaly_score = iso_forest.score_samples([[birth_year]])[0]
                    
                    if prediction[0] == -1:  # -1 indicates outlier
                        results["details"]["birth_year_outlier"] = True
                        results["is_anomaly"] = True
                    
                    results["anomaly_score"] = float(-anomaly_score)  # Convert to positive score
            
            # Check name pattern anomalies
            name = parsed_data.get("name", "")
            if name:
                name_issues = []
                
                # Check for unusual characters (numbers, special chars in name)
                if re.search(r'[0-9]', name):
                    name_issues.append("contains_numbers")
                
                if re.search(r'[^a-zA-Z\s\.\']', name):
                    name_issues.append("contains_special_chars")
                
                # Check name length (too short or too long)
                if len(name) < 3:
                    name_issues.append("too_short")
                elif len(name) > 100:
                    name_issues.append("too_long")
                
                # Check for repeated characters (e.g., "AAAAA")
                if re.search(r'(.)\1{4,}', name):
                    name_issues.append("repeated_characters")
                
                if name_issues:
                    results["details"]["name_anomalies"] = name_issues
                    results["is_anomaly"] = True
            
            # Check ID number format
            id_number = parsed_data.get("id_number", "")
            if id_number:
                # Check if ID follows expected pattern (varies by region)
                # Example: ABC1234567 format
                if not re.match(r'^[A-Z]{3}\d{7}$', id_number, re.IGNORECASE):
                    results["details"]["id_format_unusual"] = True
            
            # Check address completeness
            address = parsed_data.get("address", "")
            if address:
                # Check if address has minimum expected components
                has_numbers = bool(re.search(r'\d', address))
                has_pin = bool(re.search(r'\d{5,6}', address))
                
                if not has_numbers or not has_pin:
                    results["details"]["incomplete_address"] = True
            
        except Exception as e:
            print(f"Anomaly detection error: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def detect_duplicates_in_batch(
        self,
        records: List[Dict[str, str]],
        threshold: float = 0.9
    ) -> List[tuple]:
        """
        Find potential duplicate records in a batch of voter entries
        Uses fuzzy matching on name, DoB, address
        Returns list of (index1, index2, similarity_score) tuples
        """
        duplicates = []
        
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                record1 = records[i]
                record2 = records[j]
                
                # Calculate similarity for each field
                name_sim = self.calculate_similarity(
                    record1.get("name", ""),
                    record2.get("name", "")
                )
                
                dob_sim = self.calculate_similarity(
                    record1.get("date_of_birth", ""),
                    record2.get("date_of_birth", "")
                )
                
                addr_sim = self.calculate_similarity(
                    record1.get("address", ""),
                    record2.get("address", "")
                )
                
                # Calculate weighted average similarity
                overall_sim = (name_sim * 0.4 + dob_sim * 0.3 + addr_sim * 0.3)
                
                if overall_sim >= threshold:
                    duplicates.append((i, j, overall_sim))
        
        return duplicates
    
    def validate_date_format(self, date_string: str) -> bool:
        """Check if date string is in valid format"""
        if not date_string:
            return False
        
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
            "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d"
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(date_string, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def check_data_completeness(self, parsed_data: Dict[str, Optional[str]]) -> Dict[str, bool]:
        """
        Check if all required fields are present and valid
        Returns completeness report
        """
        required_fields = ["name", "date_of_birth", "id_number", "address"]
        
        completeness = {
            "all_fields_present": True,
            "missing_fields": [],
            "empty_fields": []
        }
        
        for field in required_fields:
            value = parsed_data.get(field)
            
            if value is None:
                completeness["missing_fields"].append(field)
                completeness["all_fields_present"] = False
            elif not value.strip():
                completeness["empty_fields"].append(field)
                completeness["all_fields_present"] = False
        
        return completeness

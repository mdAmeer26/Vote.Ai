"""
Duplicate Detection Module
Stores voter entries and detects duplicates across multiple fields
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib


class DuplicateDetector:
    """Handles duplicate detection across voter entries"""
    
    def __init__(self, storage_file="voter_database.json"):
        """Initialize duplicate detector with persistent storage"""
        self.storage_file = storage_file
        self.voters_db = self.load_database()
    
    def load_database(self) -> Dict:
        """Load voter database from file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                return {"voters": [], "next_id": 1}
        return {"voters": [], "next_id": 1}
    
    def save_database(self):
        """Save voter database to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.voters_db, f, indent=2)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def add_voter(self, voter_data: Dict) -> int:
        """Add a new voter to the database"""
        voter_id = self.voters_db["next_id"]
        voter_entry = {
            "id": voter_id,
            "timestamp": datetime.now().isoformat(),
            "data": voter_data
        }
        self.voters_db["voters"].append(voter_entry)
        self.voters_db["next_id"] += 1
        self.save_database()
        return voter_id
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Simple similarity based on common characters
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
    
    def check_duplicates(self, new_voter_data: Dict, threshold: float = 0.85) -> Dict:
        """
        Check for duplicates across all fields
        Returns detailed information about potential duplicates
        """
        duplicates = {
            "has_duplicates": False,
            "exact_matches": [],
            "similar_entries": [],
            "field_duplicates": {
                "name": [],
                "date_of_birth": [],
                "id_number": [],
                "address": [],
                "face_hash": []
            }
        }
        
        name_new = new_voter_data.get("name", "").lower().strip()
        dob_new = new_voter_data.get("date_of_birth", "").lower().strip()
        id_new = new_voter_data.get("id_number", "").lower().strip()
        addr_new = new_voter_data.get("address", "").lower().strip()
        face_new = new_voter_data.get("face_hash", "")
        
        for voter in self.voters_db["voters"]:
            voter_data = voter["data"]
            voter_id = voter["id"]
            
            # Check each field for duplicates
            name_existing = voter_data.get("name", "").lower().strip()
            dob_existing = voter_data.get("date_of_birth", "").lower().strip()
            id_existing = voter_data.get("id_number", "").lower().strip()
            addr_existing = voter_data.get("address", "").lower().strip()
            face_existing = voter_data.get("face_hash", "")
            
            match_details = {
                "voter_id": voter_id,
                "timestamp": voter.get("timestamp"),
                "matches": {}
            }
            
            # Check name
            if name_new and name_existing:
                name_sim = self.calculate_similarity(name_new, name_existing)
                if name_sim >= threshold:
                    match_details["matches"]["name"] = {
                        "similarity": round(name_sim * 100, 2),
                        "value": voter_data.get("name")
                    }
                    duplicates["field_duplicates"]["name"].append({
                        "voter_id": voter_id,
                        "value": voter_data.get("name"),
                        "similarity": round(name_sim * 100, 2)
                    })
            
            # Check date of birth (exact match)
            if dob_new and dob_existing and dob_new == dob_existing:
                match_details["matches"]["date_of_birth"] = {
                    "similarity": 100.0,
                    "value": voter_data.get("date_of_birth")
                }
                duplicates["field_duplicates"]["date_of_birth"].append({
                    "voter_id": voter_id,
                    "value": voter_data.get("date_of_birth")
                })
            
            # Check ID number (exact match)
            if id_new and id_existing and id_new == id_existing:
                match_details["matches"]["id_number"] = {
                    "similarity": 100.0,
                    "value": voter_data.get("id_number")
                }
                duplicates["field_duplicates"]["id_number"].append({
                    "voter_id": voter_id,
                    "value": voter_data.get("id_number")
                })
            
            # Check address
            if addr_new and addr_existing:
                addr_sim = self.calculate_similarity(addr_new, addr_existing)
                if addr_sim >= threshold:
                    match_details["matches"]["address"] = {
                        "similarity": round(addr_sim * 100, 2),
                        "value": voter_data.get("address")
                    }
                    duplicates["field_duplicates"]["address"].append({
                        "voter_id": voter_id,
                        "value": voter_data.get("address"),
                        "similarity": round(addr_sim * 100, 2)
                    })
            
            # Check face hash (if available)
            if face_new and face_existing and face_new == face_existing:
                match_details["matches"]["face_hash"] = {
                    "similarity": 100.0,
                    "note": "Identical face detected"
                }
                duplicates["field_duplicates"]["face_hash"].append({
                    "voter_id": voter_id,
                    "note": "Identical face detected"
                })
            
            # If multiple fields match, this is a suspicious entry
            num_matches = len(match_details["matches"])
            if num_matches > 0:
                match_details["match_count"] = num_matches
                duplicates["similar_entries"].append(match_details)
                duplicates["has_duplicates"] = True
                
                # If 3+ fields match, it's likely an exact duplicate
                if num_matches >= 3:
                    duplicates["exact_matches"].append(match_details)
        
        # Calculate overall duplicate risk score
        total_field_duplicates = sum(len(v) for v in duplicates["field_duplicates"].values())
        duplicates["duplicate_risk_score"] = min(100, total_field_duplicates * 20)
        
        return duplicates
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        return {
            "total_voters": len(self.voters_db["voters"]),
            "next_id": self.voters_db["next_id"]
        }
    
    def clear_database(self):
        """Clear all voter records (for testing)"""
        self.voters_db = {"voters": [], "next_id": 1}
        self.save_database()
    
    def hash_image(self, image_bytes: bytes) -> str:
        """Create a hash of the image for duplicate detection"""
        return hashlib.sha256(image_bytes).hexdigest()

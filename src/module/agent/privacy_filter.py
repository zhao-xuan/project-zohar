"""
Privacy Filter for Project Zohar.

This module provides privacy protection through PII detection,
data anonymization, and sensitive information filtering.
"""

import re
import hashlib
import json
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime
from enum import Enum
import logging

from config.settings import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class PrivacyLevel(Enum):
    """Privacy protection levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


class PIIType(Enum):
    """Types of Personally Identifiable Information."""
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account"
    CUSTOM = "custom"


class PrivacyFilter:
    """
    Privacy filter for detecting and handling sensitive information.
    
    This class provides:
    - PII detection and classification
    - Data anonymization and redaction
    - Selective data sharing controls
    - Privacy level enforcement
    """
    
    def __init__(self, privacy_level: PrivacyLevel = PrivacyLevel.HIGH):
        """
        Initialize the privacy filter.
        
        Args:
            privacy_level: Default privacy protection level
        """
        self.privacy_level = privacy_level
        self.settings = get_settings()
        
        # PII detection patterns
        self.pii_patterns = {
            PIIType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            PIIType.PHONE: [
                r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
                r'\b\(\d{3}\)\s?\d{3}-\d{4}\b',  # (123) 456-7890
                r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
                r'\b\+\d{1,3}\s?\d{3,4}\s?\d{3,4}\s?\d{4}\b'  # +1 123 456 7890
            ],
            PIIType.CREDIT_CARD: [
                r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
                r'\b5[1-5][0-9]{14}\b',  # MasterCard
                r'\b3[47][0-9]{13}\b',  # American Express
                r'\b3[0-9]{4}[0-9]{6}[0-9]{5}\b'  # Diners Club
            ],
            PIIType.SSN: [
                r'\b\d{3}-\d{2}-\d{4}\b',  # 123-45-6789
                r'\b\d{9}\b'  # 123456789
            ],
            PIIType.IP_ADDRESS: [
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IPv4
                r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'  # IPv6
            ],
            PIIType.DATE_OF_BIRTH: [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
                r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'  # YYYY/MM/DD or YYYY-MM-DD
            ],
            PIIType.PASSPORT: [
                r'\b[A-Z]{2}\d{7}\b',  # US Passport format
                r'\b[A-Z]\d{8}\b'  # Generic passport format
            ],
            PIIType.DRIVER_LICENSE: [
                r'\b[A-Z]{1,2}\d{6,8}\b',  # Generic license format
                r'\b\d{8,10}\b'  # Numeric license format
            ],
            PIIType.BANK_ACCOUNT: [
                r'\b\d{8,17}\b'  # Generic bank account number
            ]
        }
        
        # Common names for enhanced detection
        self.common_names = {
            "first_names": {
                "james", "john", "robert", "michael", "william", "david", "richard", "charles",
                "joseph", "thomas", "mary", "patricia", "jennifer", "linda", "elizabeth",
                "barbara", "susan", "jessica", "sarah", "karen", "nancy", "lisa", "betty",
                "dorothy", "sandra", "ashley", "kimberly", "emily", "donna", "margaret",
                "carol", "ruth", "sharon", "michelle", "laura", "sarah", "kimberly"
            },
            "last_names": {
                "smith", "johnson", "williams", "brown", "jones", "garcia", "miller",
                "davis", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez",
                "wilson", "anderson", "thomas", "taylor", "moore", "jackson", "martin",
                "lee", "perez", "thompson", "white", "harris", "sanchez", "clark",
                "ramirez", "lewis", "robinson", "walker", "young", "allen", "king"
            }
        }
        
        # Custom patterns for organization-specific data
        self.custom_patterns = {}
        
        # Anonymization cache
        self.anonymization_cache = {}
        
        logger.info(f"Privacy filter initialized with level: {privacy_level.value}")
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of detected PII items with type, content, and position
        """
        detected_pii = []
        
        try:
            # Check each PII type
            for pii_type, patterns in self.pii_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        detected_pii.append({
                            "type": pii_type.value,
                            "content": match.group(),
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": self._calculate_confidence(pii_type, match.group())
                        })
            
            # Detect potential names
            name_matches = self._detect_names(text)
            detected_pii.extend(name_matches)
            
            # Check custom patterns
            for pattern_name, pattern in self.custom_patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    detected_pii.append({
                        "type": PIIType.CUSTOM.value,
                        "subtype": pattern_name,
                        "content": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.8
                    })
            
            # Sort by position
            detected_pii.sort(key=lambda x: x["start"])
            
            logger.debug(f"Detected {len(detected_pii)} PII items in text")
            return detected_pii
            
        except Exception as e:
            logger.error(f"Failed to detect PII: {e}")
            return []
    
    def anonymize_text(
        self,
        text: str,
        replacement_strategy: str = "redact",
        preserve_format: bool = True
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Anonymize text by replacing PII with safe alternatives.
        
        Args:
            text: Input text to anonymize
            replacement_strategy: How to replace PII ("redact", "hash", "substitute", "mask")
            preserve_format: Whether to preserve original format
            
        Returns:
            Tuple of (anonymized_text, detected_pii_list)
        """
        try:
            detected_pii = self.detect_pii(text)
            anonymized_text = text
            offset = 0
            
            for pii_item in detected_pii:
                original_content = pii_item["content"]
                start_pos = pii_item["start"] + offset
                end_pos = pii_item["end"] + offset
                
                # Generate replacement based on strategy
                replacement = self._generate_replacement(
                    pii_item, replacement_strategy, preserve_format
                )
                
                # Replace in text
                anonymized_text = (
                    anonymized_text[:start_pos] + 
                    replacement + 
                    anonymized_text[end_pos:]
                )
                
                # Update offset for next replacements
                offset += len(replacement) - len(original_content)
                
                # Update PII item with replacement info
                pii_item["replacement"] = replacement
                pii_item["anonymized"] = True
            
            logger.info(f"Anonymized {len(detected_pii)} PII items using {replacement_strategy} strategy")
            return anonymized_text, detected_pii
            
        except Exception as e:
            logger.error(f"Failed to anonymize text: {e}")
            return text, []
    
    def filter_data(
        self,
        data: Dict[str, Any],
        allowed_fields: Optional[Set[str]] = None,
        blocked_fields: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Filter data based on privacy level and field restrictions.
        
        Args:
            data: Input data dictionary
            allowed_fields: Set of fields to allow (if specified, only these are kept)
            blocked_fields: Set of fields to block (these are removed)
            
        Returns:
            Filtered data dictionary
        """
        try:
            filtered_data = {}
            
            for key, value in data.items():
                # Check field restrictions
                if allowed_fields and key not in allowed_fields:
                    continue
                    
                if blocked_fields and key in blocked_fields:
                    continue
                
                # Apply privacy level filtering
                if self._should_filter_field(key, value):
                    if self.privacy_level == PrivacyLevel.MAXIMUM:
                        continue  # Skip entirely
                    else:
                        # Anonymize the value
                        if isinstance(value, str):
                            anonymized_value, _ = self.anonymize_text(value)
                            filtered_data[key] = anonymized_value
                        else:
                            filtered_data[key] = self._anonymize_value(value)
                else:
                    filtered_data[key] = value
            
            logger.debug(f"Filtered data: {len(data)} -> {len(filtered_data)} fields")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Failed to filter data: {e}")
            return data
    
    def check_privacy_compliance(
        self,
        text: str,
        max_pii_count: int = 0,
        allowed_pii_types: Optional[List[PIIType]] = None
    ) -> Dict[str, Any]:
        """
        Check if text complies with privacy requirements.
        
        Args:
            text: Text to check
            max_pii_count: Maximum allowed PII items
            allowed_pii_types: List of allowed PII types
            
        Returns:
            Compliance report
        """
        try:
            detected_pii = self.detect_pii(text)
            
            # Count PII by type
            pii_counts = {}
            for pii_item in detected_pii:
                pii_type = pii_item["type"]
                pii_counts[pii_type] = pii_counts.get(pii_type, 0) + 1
            
            # Check compliance
            violations = []
            
            # Check total PII count
            if len(detected_pii) > max_pii_count:
                violations.append({
                    "type": "pii_count_exceeded",
                    "message": f"Found {len(detected_pii)} PII items, max allowed: {max_pii_count}"
                })
            
            # Check allowed PII types
            if allowed_pii_types:
                allowed_types = {pii_type.value for pii_type in allowed_pii_types}
                for pii_type in pii_counts:
                    if pii_type not in allowed_types:
                        violations.append({
                            "type": "disallowed_pii_type",
                            "message": f"Found disallowed PII type: {pii_type}"
                        })
            
            # Check privacy level compliance
            if self.privacy_level == PrivacyLevel.MAXIMUM and detected_pii:
                violations.append({
                    "type": "privacy_level_violation",
                    "message": f"Maximum privacy level requires no PII, found {len(detected_pii)} items"
                })
            
            compliance_report = {
                "compliant": len(violations) == 0,
                "detected_pii": detected_pii,
                "pii_counts": pii_counts,
                "violations": violations,
                "privacy_level": self.privacy_level.value,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Privacy compliance check: {'PASS' if compliance_report['compliant'] else 'FAIL'}")
            return compliance_report
            
        except Exception as e:
            logger.error(f"Failed to check privacy compliance: {e}")
            return {"compliant": False, "error": str(e)}
    
    def add_custom_pattern(self, name: str, pattern: str):
        """
        Add a custom PII detection pattern.
        
        Args:
            name: Name of the pattern
            pattern: Regular expression pattern
        """
        try:
            # Validate pattern
            re.compile(pattern)
            self.custom_patterns[name] = pattern
            logger.info(f"Added custom pattern: {name}")
            
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def remove_custom_pattern(self, name: str):
        """Remove a custom PII detection pattern."""
        if name in self.custom_patterns:
            del self.custom_patterns[name]
            logger.info(f"Removed custom pattern: {name}")
    
    def get_privacy_summary(self, text: str) -> Dict[str, Any]:
        """
        Get a summary of privacy-related information in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Privacy summary dictionary
        """
        try:
            detected_pii = self.detect_pii(text)
            
            # Count by type
            type_counts = {}
            high_confidence_count = 0
            
            for pii_item in detected_pii:
                pii_type = pii_item["type"]
                type_counts[pii_type] = type_counts.get(pii_type, 0) + 1
                
                if pii_item.get("confidence", 0) > 0.8:
                    high_confidence_count += 1
            
            # Calculate privacy score (0-100, where 100 is most private)
            privacy_score = max(0, 100 - (len(detected_pii) * 10))
            
            # Determine risk level
            if len(detected_pii) == 0:
                risk_level = "none"
            elif len(detected_pii) <= 2:
                risk_level = "low"
            elif len(detected_pii) <= 5:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            return {
                "total_pii_count": len(detected_pii),
                "high_confidence_count": high_confidence_count,
                "pii_types": type_counts,
                "privacy_score": privacy_score,
                "risk_level": risk_level,
                "privacy_level": self.privacy_level.value,
                "recommendations": self._get_privacy_recommendations(detected_pii)
            }
            
        except Exception as e:
            logger.error(f"Failed to get privacy summary: {e}")
            return {}
    
    def create_safe_version(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a safe version of text for sharing or storage.
        
        Args:
            text: Original text
            context: Context for smart anonymization
            
        Returns:
            Dictionary with safe text and metadata
        """
        try:
            # Determine appropriate anonymization strategy
            strategy = self._determine_anonymization_strategy(text, context)
            
            # Anonymize text
            safe_text, detected_pii = self.anonymize_text(
                text, 
                replacement_strategy=strategy,
                preserve_format=True
            )
            
            # Create metadata
            metadata = {
                "original_length": len(text),
                "safe_length": len(safe_text),
                "anonymization_strategy": strategy,
                "pii_detected": len(detected_pii),
                "privacy_level": self.privacy_level.value,
                "created_at": datetime.now().isoformat()
            }
            
            return {
                "safe_text": safe_text,
                "metadata": metadata,
                "detected_pii": detected_pii,
                "reversible": strategy in ["hash", "substitute"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create safe version: {e}")
            return {"safe_text": text, "error": str(e)}
    
    # Private methods
    
    def _detect_names(self, text: str) -> List[Dict[str, Any]]:
        """Detect potential names in text."""
        detected_names = []
        
        try:
            # Simple name detection based on capitalization and word lists
            words = re.findall(r'\b[A-Z][a-z]+\b', text)
            
            for word in words:
                word_lower = word.lower()
                
                # Check against common names
                if (word_lower in self.common_names["first_names"] or
                    word_lower in self.common_names["last_names"]):
                    
                    # Find position in text
                    matches = re.finditer(r'\b' + re.escape(word) + r'\b', text)
                    for match in matches:
                        detected_names.append({
                            "type": PIIType.NAME.value,
                            "content": match.group(),
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": 0.6  # Lower confidence for name detection
                        })
            
            return detected_names
            
        except Exception as e:
            logger.error(f"Failed to detect names: {e}")
            return []
    
    def _calculate_confidence(self, pii_type: PIIType, content: str) -> float:
        """Calculate confidence score for PII detection."""
        # Base confidence by type
        base_confidence = {
            PIIType.EMAIL: 0.9,
            PIIType.PHONE: 0.8,
            PIIType.CREDIT_CARD: 0.95,
            PIIType.SSN: 0.9,
            PIIType.IP_ADDRESS: 0.85,
            PIIType.DATE_OF_BIRTH: 0.7,
            PIIType.PASSPORT: 0.8,
            PIIType.DRIVER_LICENSE: 0.7,
            PIIType.BANK_ACCOUNT: 0.6,
            PIIType.NAME: 0.6
        }
        
        confidence = base_confidence.get(pii_type, 0.5)
        
        # Adjust based on content characteristics
        if pii_type == PIIType.EMAIL and "@" in content and "." in content:
            confidence = min(0.95, confidence + 0.1)
        
        if pii_type == PIIType.PHONE and len(content) >= 10:
            confidence = min(0.9, confidence + 0.1)
        
        return confidence
    
    def _generate_replacement(
        self,
        pii_item: Dict[str, Any],
        strategy: str,
        preserve_format: bool
    ) -> str:
        """Generate replacement text for PII."""
        content = pii_item["content"]
        pii_type = pii_item["type"]
        
        if strategy == "redact":
            return "[REDACTED]"
        
        elif strategy == "hash":
            # Use cached hash if available
            if content in self.anonymization_cache:
                return self.anonymization_cache[content]
            
            hash_value = hashlib.sha256(content.encode()).hexdigest()[:8]
            replacement = f"[HASH_{hash_value}]"
            self.anonymization_cache[content] = replacement
            return replacement
        
        elif strategy == "substitute":
            return self._get_substitute_value(pii_type, content, preserve_format)
        
        elif strategy == "mask":
            return self._mask_value(content, preserve_format)
        
        else:
            return "[ANONYMIZED]"
    
    def _get_substitute_value(self, pii_type: str, content: str, preserve_format: bool) -> str:
        """Get substitute value for PII."""
        substitutes = {
            PIIType.EMAIL.value: "user@example.com",
            PIIType.PHONE.value: "555-0123",
            PIIType.NAME.value: "John Doe",
            PIIType.ADDRESS.value: "123 Main St",
            PIIType.DATE_OF_BIRTH.value: "01/01/1990",
            PIIType.PASSPORT.value: "AB1234567",
            PIIType.DRIVER_LICENSE.value: "DL123456",
            PIIType.BANK_ACCOUNT.value: "12345678"
        }
        
        base_substitute = substitutes.get(pii_type, "[SUBSTITUTE]")
        
        if preserve_format and pii_type == PIIType.PHONE.value:
            # Preserve phone number format
            if "-" in content:
                return "555-555-5555"
            elif "(" in content:
                return "(555) 555-5555"
            elif "." in content:
                return "555.555.5555"
        
        return base_substitute
    
    def _mask_value(self, content: str, preserve_format: bool) -> str:
        """Mask value with asterisks."""
        if len(content) <= 4:
            return "*" * len(content)
        
        if preserve_format:
            # Keep first and last character, mask middle
            return content[0] + "*" * (len(content) - 2) + content[-1]
        else:
            # Mask most characters, keep last few
            visible_chars = min(2, len(content) // 3)
            return "*" * (len(content) - visible_chars) + content[-visible_chars:]
    
    def _should_filter_field(self, field_name: str, value: Any) -> bool:
        """Check if a field should be filtered based on privacy level."""
        sensitive_fields = {
            "password", "secret", "token", "key", "private", "confidential",
            "personal", "pii", "sensitive", "credit_card", "ssn", "phone",
            "email", "address", "name", "birth", "passport", "license"
        }
        
        field_lower = field_name.lower()
        
        # Check if field name indicates sensitive data
        for sensitive_term in sensitive_fields:
            if sensitive_term in field_lower:
                return True
        
        # Check if value contains PII
        if isinstance(value, str):
            detected_pii = self.detect_pii(value)
            if detected_pii:
                return True
        
        return False
    
    def _anonymize_value(self, value: Any) -> Any:
        """Anonymize a non-string value."""
        if isinstance(value, (int, float)):
            return "[NUMERIC_VALUE]"
        elif isinstance(value, bool):
            return "[BOOLEAN_VALUE]"
        elif isinstance(value, (list, tuple)):
            return "[LIST_VALUE]"
        elif isinstance(value, dict):
            return "[DICT_VALUE]"
        else:
            return "[UNKNOWN_VALUE]"
    
    def _determine_anonymization_strategy(self, text: str, context: Optional[str]) -> str:
        """Determine the best anonymization strategy."""
        if self.privacy_level == PrivacyLevel.MAXIMUM:
            return "redact"
        elif self.privacy_level == PrivacyLevel.HIGH:
            return "hash"
        elif self.privacy_level == PrivacyLevel.MEDIUM:
            return "substitute"
        else:
            return "mask"
    
    def _get_privacy_recommendations(self, detected_pii: List[Dict[str, Any]]) -> List[str]:
        """Get privacy recommendations based on detected PII."""
        recommendations = []
        
        if not detected_pii:
            recommendations.append("No PII detected. Text appears to be privacy-safe.")
            return recommendations
        
        pii_types = {item["type"] for item in detected_pii}
        
        if PIIType.EMAIL.value in pii_types:
            recommendations.append("Consider masking or removing email addresses.")
        
        if PIIType.PHONE.value in pii_types:
            recommendations.append("Consider masking phone numbers.")
        
        if PIIType.CREDIT_CARD.value in pii_types:
            recommendations.append("Credit card numbers should be immediately redacted.")
        
        if PIIType.SSN.value in pii_types:
            recommendations.append("SSNs should be immediately redacted.")
        
        if PIIType.NAME.value in pii_types:
            recommendations.append("Consider using initials or pseudonyms instead of full names.")
        
        if len(detected_pii) > 5:
            recommendations.append("High PII count detected. Consider comprehensive anonymization.")
        
        recommendations.append(f"Current privacy level: {self.privacy_level.value}. Consider increasing if needed.")
        
        return recommendations

    async def filter_input(self, input_text: str) -> str:
        """
        Filter input text to remove or anonymize sensitive information.
        
        Args:
            input_text: Input text to filter
            
        Returns:
            Filtered text safe for processing
        """
        try:
            # Determine anonymization strategy based on privacy level
            if self.privacy_level == PrivacyLevel.MAXIMUM:
                strategy = "redact"
            elif self.privacy_level == PrivacyLevel.HIGH:
                strategy = "hash"
            elif self.privacy_level == PrivacyLevel.MEDIUM:
                strategy = "substitute"
            else:
                strategy = "mask"
            
            # Anonymize the input text
            filtered_text, detected_pii = self.anonymize_text(
                input_text, 
                replacement_strategy=strategy,
                preserve_format=True
            )
            
            if detected_pii:
                logger.info(f"Filtered {len(detected_pii)} PII items from input using {strategy} strategy")
            
            return filtered_text
            
        except Exception as e:
            logger.error(f"Failed to filter input: {e}")
            return input_text

    async def filter_output(self, output_text: str) -> str:
        """
        Filter output text to ensure no sensitive information is revealed.
        
        Args:
            output_text: Output text to filter
            
        Returns:
            Filtered text safe for display
        """
        try:
            # Use more conservative filtering for output
            # Always use redaction for output to prevent accidental exposure
            filtered_text, detected_pii = self.anonymize_text(
                output_text, 
                replacement_strategy="redact",
                preserve_format=False
            )
            
            if detected_pii:
                logger.warning(f"Filtered {len(detected_pii)} PII items from output - check agent for data leakage")
            
            return filtered_text
            
        except Exception as e:
            logger.error(f"Failed to filter output: {e}")
            return output_text

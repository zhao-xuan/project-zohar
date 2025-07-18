"""
Structure Generator

AI-powered data structure generation that analyzes file descriptions
and creates optimized data structures for vector database storage.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from zohar.utils.logging import get_logger
from .content_analyzer import ContentDescription

logger = get_logger(__name__)


@dataclass 
class DataField:
    """Definition of a data field in the structure."""
    name: str
    type: str
    description: str
    required: bool
    default_value: Optional[Any]
    constraints: Dict[str, Any]
    source_mapping: Optional[str]


@dataclass
class DataStructure:
    """Generated data structure definition."""
    name: str
    description: str
    version: str
    fields: List[DataField]
    metadata_fields: List[DataField]
    processing_instructions: Dict[str, Any]
    vectorization_strategy: Dict[str, Any]
    quality_requirements: Dict[str, Any]
    suggested_chunking: Dict[str, Any]


@dataclass
class StructureRecommendation:
    """Structure recommendation with confidence and reasoning."""
    structure: DataStructure
    confidence: float
    reasoning: str
    alternative_structures: List[DataStructure]
    user_feedback_required: List[str]


class StructureGenerator:
    """
    Generates optimized data structures based on content analysis results.
    Uses AI to understand data patterns and create appropriate schemas.
    """
    
    def __init__(self):
        # Template structures for common patterns
        self.structure_templates = {
            'tabular': self._get_tabular_template,
            'document': self._get_document_template,
            'log': self._get_log_template,
            'hierarchical': self._get_hierarchical_template,
            'time_series': self._get_time_series_template
        }
        
        # Field type mappings
        self.type_mappings = {
            'str': 'text',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
            'datetime': 'timestamp',
            'date': 'date',
            'time': 'time'
        }
    
    async def generate_structure(self, content_descriptions: List[ContentDescription], 
                               user_requirements: Optional[Dict[str, Any]] = None) -> StructureRecommendation:
        """Generate optimized data structure based on content analysis."""
        logger.info(f"Generating structure for {len(content_descriptions)} files")
        
        # Analyze content patterns across all files
        pattern_analysis = await self._analyze_content_patterns(content_descriptions)
        
        # Determine primary structure type
        structure_type = self._determine_structure_type(pattern_analysis, content_descriptions)
        
        # Generate base structure
        base_structure = await self._generate_base_structure(
            structure_type, pattern_analysis, content_descriptions
        )
        
        # Apply user requirements if provided
        if user_requirements:
            base_structure = await self._apply_user_requirements(base_structure, user_requirements)
        
        # Generate alternatives
        alternatives = await self._generate_alternative_structures(
            structure_type, pattern_analysis, content_descriptions
        )
        
        # Calculate confidence and reasoning
        confidence = self._calculate_confidence(pattern_analysis, content_descriptions)
        reasoning = await self._generate_reasoning(
            structure_type, pattern_analysis, base_structure
        )
        
        # Identify areas requiring user feedback
        feedback_required = self._identify_feedback_requirements(
            pattern_analysis, content_descriptions
        )
        
        return StructureRecommendation(
            structure=base_structure,
            confidence=confidence,
            reasoning=reasoning,
            alternative_structures=alternatives,
            user_feedback_required=feedback_required
        )
    
    async def _analyze_content_patterns(self, content_descriptions: List[ContentDescription]) -> Dict[str, Any]:
        """Analyze patterns across all content descriptions."""
        patterns = {
            'formats': {},
            'structures': {},
            'fields': {},
            'metadata_types': {},
            'content_types': {},
            'quality_issues': [],
            'common_elements': []
        }
        
        for desc in content_descriptions:
            # Analyze formats
            format_type = desc.format_info.detected_format
            patterns['formats'][format_type] = patterns['formats'].get(format_type, 0) + 1
            
            # Analyze structures
            structure_type = desc.content_analysis.get('structure_type', 'unknown')
            patterns['structures'][structure_type] = patterns['structures'].get(structure_type, 0) + 1
            
            # Extract field information
            if desc.parsing_results.get('success'):
                fields = self._extract_field_info(desc)
                for field_name, field_info in fields.items():
                    if field_name not in patterns['fields']:
                        patterns['fields'][field_name] = {
                            'types': {},
                            'occurrences': 0
                        }
                    
                    patterns['fields'][field_name]['occurrences'] += 1
                    field_type = field_info.get('type', 'unknown')
                    patterns['fields'][field_name]['types'][field_type] = \
                        patterns['fields'][field_name]['types'].get(field_type, 0) + 1
            
            # Collect quality issues
            patterns['quality_issues'].extend(desc.quality_issues)
        
        return patterns
    
    def _determine_structure_type(self, patterns: Dict[str, Any], 
                                content_descriptions: List[ContentDescription]) -> str:
        """Determine the primary structure type for the data."""
        structure_counts = patterns['structures']
        format_counts = patterns['formats']
        
        # Priority-based determination
        if 'tabular' in structure_counts and structure_counts['tabular'] > 0:
            return 'tabular'
        elif 'csv' in format_counts:
            return 'tabular'
        elif any(fmt in format_counts for fmt in ['json', 'xml']):
            return 'hierarchical'
        elif 'log' in format_counts:
            return 'log'
        else:
            return 'document'  # Default fallback
    
    async def _generate_base_structure(self, structure_type: str, 
                                     patterns: Dict[str, Any],
                                     content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate base structure using appropriate template."""
        template_func = self.structure_templates.get(structure_type, self._get_document_template)
        
        # Generate structure from template
        structure = template_func(patterns, content_descriptions)
        
        # Add common metadata fields
        structure.metadata_fields.extend(self._generate_metadata_fields(patterns))
        
        # Generate processing instructions
        structure.processing_instructions = self._generate_processing_instructions(
            structure_type, patterns, content_descriptions
        )
        
        # Generate vectorization strategy
        structure.vectorization_strategy = self._generate_vectorization_strategy(
            structure_type, structure.fields
        )
        
        return structure
    
    def _get_tabular_template(self, patterns: Dict[str, Any], 
                            content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate tabular data structure template."""
        fields = []
        
        # Generate fields from pattern analysis
        for field_name, field_info in patterns.get('fields', {}).items():
            # Determine most common type
            type_counts = field_info['types']
            most_common_type = max(type_counts.keys(), key=lambda k: type_counts[k]) if type_counts else 'text'
            
            # Map to standard type
            standard_type = self.type_mappings.get(most_common_type, 'text')
            
            field = DataField(
                name=field_name,
                type=standard_type,
                description=f"Field extracted from {field_info['occurrences']} files",
                required=field_info['occurrences'] > len(content_descriptions) * 0.5,
                default_value=None,
                constraints={},
                source_mapping=field_name
            )
            
            fields.append(field)
        
        return DataStructure(
            name="TabularDataStructure",
            description="Structure for tabular data files",
            version="1.0",
            fields=fields,
            metadata_fields=[],
            processing_instructions={},
            vectorization_strategy={},
            quality_requirements={},
            suggested_chunking={}
        )
    
    def _get_document_template(self, patterns: Dict[str, Any], 
                             content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate document data structure template."""
        fields = [
            DataField(
                name="content",
                type="text",
                description="Main document content",
                required=True,
                default_value=None,
                constraints={"max_length": 100000},
                source_mapping="full_content"
            ),
            DataField(
                name="title",
                type="text",
                description="Document title or filename",
                required=True,
                default_value=None,
                constraints={"max_length": 500},
                source_mapping="filename"
            ),
            DataField(
                name="document_type",
                type="text",
                description="Type of document",
                required=True,
                default_value="text",
                constraints={"enum": list(patterns['formats'].keys())},
                source_mapping="format"
            )
        ]
        
        return DataStructure(
            name="DocumentStructure",
            description="Structure for document-based data",
            version="1.0",
            fields=fields,
            metadata_fields=[],
            processing_instructions={},
            vectorization_strategy={},
            quality_requirements={},
            suggested_chunking={}
        )
    
    def _get_log_template(self, patterns: Dict[str, Any], 
                        content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate log data structure template."""
        fields = [
            DataField(
                name="timestamp",
                type="timestamp",
                description="Log entry timestamp",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="timestamp_field"
            ),
            DataField(
                name="level",
                type="text",
                description="Log level",
                required=True,
                default_value="INFO",
                constraints={"enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]},
                source_mapping="log_level"
            ),
            DataField(
                name="message",
                type="text",
                description="Log message content",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="message_content"
            )
        ]
        
        return DataStructure(
            name="LogStructure",
            description="Structure for log data",
            version="1.0",
            fields=fields,
            metadata_fields=[],
            processing_instructions={},
            vectorization_strategy={},
            quality_requirements={},
            suggested_chunking={}
        )
    
    def _get_hierarchical_template(self, patterns: Dict[str, Any], 
                                 content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate hierarchical data structure template."""
        fields = [
            DataField(
                name="data",
                type="json_object",
                description="Hierarchical data structure",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="full_structure"
            )
        ]
        
        return DataStructure(
            name="HierarchicalStructure",
            description="Structure for hierarchical data (JSON, XML, etc.)",
            version="1.0",
            fields=fields,
            metadata_fields=[],
            processing_instructions={},
            vectorization_strategy={},
            quality_requirements={},
            suggested_chunking={}
        )
    
    def _get_time_series_template(self, patterns: Dict[str, Any], 
                                content_descriptions: List[ContentDescription]) -> DataStructure:
        """Generate time series data structure template."""
        fields = [
            DataField(
                name="timestamp",
                type="timestamp",
                description="Data point timestamp",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="time_field"
            ),
            DataField(
                name="value",
                type="number",
                description="Measured value",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="value_field"
            )
        ]
        
        return DataStructure(
            name="TimeSeriesStructure",
            description="Structure for time series data",
            version="1.0",
            fields=fields,
            metadata_fields=[],
            processing_instructions={},
            vectorization_strategy={},
            quality_requirements={},
            suggested_chunking={}
        )
    
    def _generate_metadata_fields(self, patterns: Dict[str, Any]) -> List[DataField]:
        """Generate common metadata fields."""
        return [
            DataField(
                name="source_file",
                type="text",
                description="Original source file path",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="file_path"
            ),
            DataField(
                name="processing_date",
                type="timestamp",
                description="Date when data was processed",
                required=True,
                default_value=None,
                constraints={},
                source_mapping="processing_timestamp"
            )
        ]
    
    def _generate_processing_instructions(self, structure_type: str, 
                                        patterns: Dict[str, Any],
                                        content_descriptions: List[ContentDescription]) -> Dict[str, Any]:
        """Generate processing instructions for the structure."""
        instructions = {
            'preprocessing': ["Validate file format and encoding"],
            'validation': ["Check data integrity"],
            'transformation': ["Apply data type conversions"],
            'error_handling': ["Log processing errors"]
        }
        
        # Structure-specific instructions
        if structure_type == 'tabular':
            instructions['preprocessing'].append("Detect column separators and headers")
            instructions['validation'].append("Validate column count consistency")
            
        elif structure_type == 'document':
            instructions['preprocessing'].append("Extract text content")
            
        elif structure_type == 'log':
            instructions['preprocessing'].append("Parse timestamp formats")
        
        return instructions
    
    def _generate_vectorization_strategy(self, structure_type: str, 
                                       fields: List[DataField]) -> Dict[str, Any]:
        """Generate vectorization strategy for the structure."""
        strategy = {
            'text_fields': [],
            'chunk_size': 1000,
            'overlap': 200,
            'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2'
        }
        
        # Identify text fields for vectorization
        for field in fields:
            if field.type in ['text'] and 'content' in field.name.lower():
                strategy['text_fields'].append(field.name)
        
        # Structure-specific strategies
        if structure_type == 'document':
            strategy['chunk_size'] = 1500
        elif structure_type == 'log':
            strategy['chunk_size'] = 500
        
        return strategy
    
    async def _apply_user_requirements(self, structure: DataStructure, 
                                     requirements: Dict[str, Any]) -> DataStructure:
        """Apply user requirements to the structure."""
        # This is a placeholder for user requirement application
        return structure
    
    async def _generate_alternative_structures(self, structure_type: str,
                                             patterns: Dict[str, Any],
                                             content_descriptions: List[ContentDescription]) -> List[DataStructure]:
        """Generate alternative structure options."""
        alternatives = []
        
        # Generate a simplified version
        if structure_type != 'document':
            simplified = self._get_document_template(patterns, content_descriptions)
            simplified.name = "SimplifiedDocumentStructure"
            alternatives.append(simplified)
        
        return alternatives
    
    def _calculate_confidence(self, patterns: Dict[str, Any], 
                            content_descriptions: List[ContentDescription]) -> float:
        """Calculate confidence score for the generated structure."""
        confidence = 1.0
        
        # Reduce confidence for inconsistent formats
        format_diversity = len(patterns['formats'])
        if format_diversity > 3:
            confidence -= 0.2
        
        # Reduce confidence for parsing failures
        failed_parses = sum(1 for desc in content_descriptions 
                          if not desc.parsing_results.get('success'))
        if failed_parses > 0:
            confidence -= (failed_parses / len(content_descriptions)) * 0.3
        
        return max(0.1, confidence)
    
    async def _generate_reasoning(self, structure_type: str, 
                                patterns: Dict[str, Any],
                                structure: DataStructure) -> str:
        """Generate reasoning for the structure choice."""
        format_counts = patterns['formats']
        most_common_format = max(format_counts.keys(), key=lambda k: format_counts[k]) if format_counts else 'unknown'
        
        reasoning = f"Selected {structure_type} structure based on analysis of {sum(format_counts.values())} files. "
        reasoning += f"Most common format: {most_common_format}. "
        reasoning += f"Structure includes {len(structure.fields)} data fields."
        
        return reasoning
    
    def _identify_feedback_requirements(self, patterns: Dict[str, Any],
                                      content_descriptions: List[ContentDescription]) -> List[str]:
        """Identify areas where user feedback would be helpful."""
        feedback_required = []
        
        # Check for quality issues
        quality_issues = set(patterns.get('quality_issues', []))
        if quality_issues:
            feedback_required.append("Review data quality issues")
        
        return feedback_required
    
    def _extract_field_info(self, content_description: ContentDescription) -> Dict[str, Any]:
        """Extract field information from content description."""
        fields = {}
        
        parsing_results = content_description.parsing_results
        if not parsing_results.get('success'):
            return fields
        
        structure = parsing_results.get('structure', {})
        
        # Handle different structure types
        if content_description.format_info.detected_format == 'csv':
            columns = structure.get('columns', [])
            for col in columns:
                fields[col] = {'type': 'str'}
                
        elif content_description.format_info.detected_format == 'json':
            if structure.get('type') == 'dict' and 'keys' in structure:
                for key in structure['keys']:
                    fields[key] = {'type': 'str'}
        
        return fields
    
    def save_structure(self, structure: DataStructure, output_path: str):
        """Save structure definition to JSON file."""
        structure_dict = asdict(structure)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structure_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Structure saved to: {output_path}")
    
    def load_structure(self, input_path: str) -> DataStructure:
        """Load structure definition from JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            structure_dict = json.load(f)
        
        # Convert field dictionaries back to DataField objects
        fields = [DataField(**field_dict) for field_dict in structure_dict['fields']]
        metadata_fields = [DataField(**field_dict) for field_dict in structure_dict['metadata_fields']]
        
        structure_dict['fields'] = fields
        structure_dict['metadata_fields'] = metadata_fields
        
        return DataStructure(**structure_dict) 
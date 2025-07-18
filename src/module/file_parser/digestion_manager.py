"""
Digestion Manager

Orchestrates the complete data digestion workflow:
1. File discovery and selection
2. Format detection and content analysis
3. Structure generation and user feedback
4. Vector database creation
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict

from zohar.utils.logging import get_logger
from zohar.config.settings import get_settings
from .file_discoverer import FileDiscoverer, FileInfo
from .format_detector import FormatDetector, FormatInfo
from .content_analyzer import ContentAnalyzer, ContentDescription
from .structure_generator import StructureGenerator, StructureRecommendation, DataStructure

logger = get_logger(__name__)


@dataclass
class DigestionSession:
    """Data digestion session information."""
    session_id: str
    created_at: str
    root_path: str
    max_files: int
    discovered_files: List[FileInfo]
    format_results: Dict[str, FormatInfo]
    content_descriptions: List[ContentDescription]
    structure_recommendation: Optional[StructureRecommendation]
    user_feedback: List[Dict[str, Any]]
    status: str  # 'discovering', 'analyzing', 'structuring', 'feedback_required', 'completed', 'error'
    error_message: Optional[str]
    output_files: Dict[str, str]


class DigestionManager:
    """
    Main orchestrator for the data digestion process.
    
    Coordinates all components to transform unknown data formats
    into optimized vector database structures.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.file_discoverer = FileDiscoverer()
        self.format_detector = FormatDetector()
        self.content_analyzer = ContentAnalyzer()
        self.structure_generator = StructureGenerator()
        
        self.sessions: Dict[str, DigestionSession] = {}
        self.output_dir = Path(self.settings.data_dir) / "digestion_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def start_digestion(self, root_path: str, 
                            max_files: int = 100,
                            session_id: Optional[str] = None) -> str:
        """
        Start a new data digestion session.
        
        Args:
            root_path: Directory to analyze
            max_files: Maximum number of files to process
            session_id: Optional custom session ID
            
        Returns:
            Session ID for tracking progress
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"digestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting digestion session {session_id} for path: {root_path}")
        
        # Initialize session
        session = DigestionSession(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            root_path=root_path,
            max_files=max_files,
            discovered_files=[],
            format_results={},
            content_descriptions=[],
            structure_recommendation=None,
            user_feedback=[],
            status='discovering',
            error_message=None,
            output_files={}
        )
        
        self.sessions[session_id] = session
        
        # Start the digestion process
        asyncio.create_task(self._run_digestion_workflow(session_id))
        
        return session_id
    
    async def _run_digestion_workflow(self, session_id: str):
        """Run the complete digestion workflow."""
        session = self.sessions[session_id]
        
        try:
            # Phase 1: File Discovery
            logger.info(f"Phase 1: File discovery for session {session_id}")
            session.status = 'discovering'
            await self._phase_1_discovery(session)
            
            # Phase 2: Format Detection and Content Analysis
            logger.info(f"Phase 2: Content analysis for session {session_id}")
            session.status = 'analyzing'
            await self._phase_2_analysis(session)
            
            # Phase 3: Structure Generation
            logger.info(f"Phase 3: Structure generation for session {session_id}")
            session.status = 'structuring'
            await self._phase_3_structure_generation(session)
            
            # Check if user feedback is required
            if session.structure_recommendation.user_feedback_required:
                session.status = 'feedback_required'
                logger.info(f"User feedback required for session {session_id}")
            else:
                # Phase 4: Finalization
                session.status = 'completed'
                await self._phase_4_finalization(session)
                logger.info(f"Digestion completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Digestion workflow failed for session {session_id}: {e}")
            session.status = 'error'
            session.error_message = str(e)
    
    async def _phase_1_discovery(self, session: DigestionSession):
        """Phase 1: Discover and select files for processing."""
        discovered_files = await self.file_discoverer.discover_files(
            session.root_path, session.max_files
        )
        
        session.discovered_files = discovered_files
        
        # Save discovery results
        discovery_path = self.output_dir / f"{session.session_id}_discovery.json"
        self.file_discoverer.save_discovery_results(str(discovery_path))
        session.output_files['discovery'] = str(discovery_path)
        
        logger.info(f"Discovered {len(discovered_files)} files for processing")
    
    async def _phase_2_analysis(self, session: DigestionSession):
        """Phase 2: Analyze file formats and content."""
        format_results = {}
        content_descriptions = []
        
        # Process files in batches to avoid overwhelming the system
        batch_size = 10
        files_to_process = [f.path for f in session.discovered_files]
        
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            
            # Format detection
            batch_format_results = self.format_detector.batch_detect(batch)
            format_results.update(batch_format_results)
            
            # Content analysis
            for file_path in batch:
                format_info = batch_format_results[file_path]
                content_desc = await self.content_analyzer.analyze_content(
                    file_path, format_info
                )
                content_descriptions.append(content_desc)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(files_to_process) + batch_size - 1)//batch_size}")
        
        session.format_results = format_results
        session.content_descriptions = content_descriptions
        
        # Save analysis results
        analysis_path = self.output_dir / f"{session.session_id}_analysis.json"
        self._save_analysis_results(session, str(analysis_path))
        session.output_files['analysis'] = str(analysis_path)
        
        logger.info(f"Completed analysis of {len(content_descriptions)} files")
    
    async def _phase_3_structure_generation(self, session: DigestionSession):
        """Phase 3: Generate optimized data structure."""
        structure_recommendation = await self.structure_generator.generate_structure(
            session.content_descriptions
        )
        
        session.structure_recommendation = structure_recommendation
        
        # Save structure recommendation
        structure_path = self.output_dir / f"{session.session_id}_structure.json"
        self._save_structure_recommendation(structure_recommendation, str(structure_path))
        session.output_files['structure'] = str(structure_path)
        
        logger.info(f"Generated structure recommendation with {structure_recommendation.confidence:.2f} confidence")
    
    async def _phase_4_finalization(self, session: DigestionSession):
        """Phase 4: Finalize the digestion process."""
        # Save final structure
        final_structure_path = self.output_dir / f"{session.session_id}_final_structure.json"
        self.structure_generator.save_structure(
            session.structure_recommendation.structure, 
            str(final_structure_path)
        )
        session.output_files['final_structure'] = str(final_structure_path)
        
        # Generate processing report
        report_path = self.output_dir / f"{session.session_id}_report.json"
        self._generate_processing_report(session, str(report_path))
        session.output_files['report'] = str(report_path)
        
        logger.info(f"Digestion finalized for session {session.session_id}")
    
    async def apply_user_feedback(self, session_id: str, 
                                feedback: Dict[str, Any]) -> StructureRecommendation:
        """
        Apply user feedback to refine the structure.
        
        Args:
            session_id: Session identifier
            feedback: User feedback on the structure
            
        Returns:
            Updated StructureRecommendation
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        session.user_feedback.append({
            'timestamp': datetime.now().isoformat(),
            'feedback': feedback
        })
        
        logger.info(f"Applying user feedback to session {session_id}")
        
        # For now, return the existing structure
        # In a full implementation, this would use the structure generator to refine
        refined_recommendation = session.structure_recommendation
        
        # Update session
        session.structure_recommendation = refined_recommendation
        session.status = 'completed'
        
        # Finalize with user feedback
        await self._phase_4_finalization(session)
        
        return refined_recommendation
    
    async def create_vector_database(self, session_id: str, 
                                   database_name: Optional[str] = None) -> str:
        """
        Create ChromaDB vector database from processed data.
        
        Args:
            session_id: Session identifier
            database_name: Optional custom database name
            
        Returns:
            Path to created database
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        if session.status != 'completed':
            raise ValueError(f"Session {session_id} is not completed (status: {session.status})")
        
        if not database_name:
            database_name = f"zohar_db_{session_id}"
        
        logger.info(f"Creating vector database {database_name} for session {session_id}")
        
        # This is a placeholder for actual vector database creation
        # In a full implementation, this would:
        # 1. Use the final structure to process all files
        # 2. Extract content according to the structure
        # 3. Create embeddings using the vectorization strategy
        # 4. Store in ChromaDB
        
        db_path = self.output_dir / f"{database_name}.db"
        
        # Create a placeholder database info file
        db_info = {
            'database_name': database_name,
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'structure': asdict(session.structure_recommendation.structure),
            'source_files': len(session.discovered_files),
            'status': 'created'
        }
        
        with open(f"{db_path}.info", 'w') as f:
            json.dump(db_info, f, indent=2, default=str)
        
        session.output_files['database'] = str(db_path)
        
        logger.info(f"Vector database created at: {db_path}")
        return str(db_path)
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a digestion session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        status = {
            'session_id': session_id,
            'status': session.status,
            'created_at': session.created_at,
            'root_path': session.root_path,
            'files_discovered': len(session.discovered_files),
            'files_analyzed': len(session.content_descriptions),
            'structure_confidence': session.structure_recommendation.confidence if session.structure_recommendation else None,
            'feedback_required': session.structure_recommendation.user_feedback_required if session.structure_recommendation else [],
            'output_files': session.output_files,
            'error_message': session.error_message
        }
        
        return status
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all digestion sessions."""
        return [
            {
                'session_id': session_id,
                'status': session.status,
                'created_at': session.created_at,
                'files_count': len(session.discovered_files)
            }
            for session_id, session in self.sessions.items()
        ]
    
    def get_structure_recommendation(self, session_id: str) -> Optional[StructureRecommendation]:
        """Get structure recommendation for a session."""
        if session_id not in self.sessions:
            return None
        
        return self.sessions[session_id].structure_recommendation
    
    def _save_analysis_results(self, session: DigestionSession, output_path: str):
        """Save analysis results to JSON file."""
        results = {
            'session_id': session.session_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'files_analyzed': len(session.content_descriptions),
            'format_distribution': self._get_format_distribution(session.format_results),
            'content_descriptions': [asdict(desc) for desc in session.content_descriptions],
            'format_results': {path: asdict(info) for path, info in session.format_results.items()}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Analysis results saved to: {output_path}")
    
    def _save_structure_recommendation(self, recommendation: StructureRecommendation, output_path: str):
        """Save structure recommendation to JSON file."""
        rec_dict = asdict(recommendation)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rec_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Structure recommendation saved to: {output_path}")
    
    def _generate_processing_report(self, session: DigestionSession, output_path: str):
        """Generate comprehensive processing report."""
        report = {
            'session_summary': {
                'session_id': session.session_id,
                'created_at': session.created_at,
                'completed_at': datetime.now().isoformat(),
                'root_path': session.root_path,
                'status': session.status
            },
            'file_processing': {
                'total_files_discovered': len(session.discovered_files),
                'files_analyzed': len(session.content_descriptions),
                'format_distribution': self._get_format_distribution(session.format_results),
                'successful_parses': sum(1 for desc in session.content_descriptions 
                                      if desc.parsing_results.get('success')),
                'average_quality_score': sum(desc.quality_score for desc in session.content_descriptions) / 
                                       len(session.content_descriptions) if session.content_descriptions else 0
            },
            'structure_recommendation': {
                'structure_type': session.structure_recommendation.structure.name if session.structure_recommendation else None,
                'confidence': session.structure_recommendation.confidence if session.structure_recommendation else None,
                'fields_count': len(session.structure_recommendation.structure.fields) if session.structure_recommendation else 0,
                'feedback_required': session.structure_recommendation.user_feedback_required if session.structure_recommendation else []
            },
            'user_interactions': {
                'feedback_rounds': len(session.user_feedback),
                'feedback_history': session.user_feedback
            },
            'output_files': session.output_files,
            'recommendations': {
                'next_steps': self._generate_next_steps(session),
                'optimization_suggestions': self._generate_optimization_suggestions(session)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Processing report saved to: {output_path}")
    
    def _get_format_distribution(self, format_results: Dict[str, FormatInfo]) -> Dict[str, int]:
        """Get distribution of detected formats."""
        distribution = {}
        for format_info in format_results.values():
            format_type = format_info.detected_format
            distribution[format_type] = distribution.get(format_type, 0) + 1
        return distribution
    
    def _generate_next_steps(self, session: DigestionSession) -> List[str]:
        """Generate recommended next steps."""
        next_steps = []
        
        if session.status == 'completed':
            next_steps.extend([
                "Create vector database using the finalized structure",
                "Test data processing pipeline with sample files",
                "Set up monitoring for data quality"
            ])
        elif session.status == 'feedback_required':
            next_steps.extend([
                "Review structure recommendation",
                "Provide feedback on field types and processing requirements",
                "Approve or modify the proposed data structure"
            ])
        elif session.status == 'error':
            next_steps.extend([
                "Review error logs and resolve issues",
                "Check file permissions and accessibility",
                "Restart digestion process if necessary"
            ])
        
        return next_steps
    
    def _generate_optimization_suggestions(self, session: DigestionSession) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        if session.content_descriptions:
            # Check for quality issues
            quality_issues = set()
            for desc in session.content_descriptions:
                quality_issues.update(desc.quality_issues)
            
            if quality_issues:
                suggestions.append(f"Address data quality issues: {', '.join(list(quality_issues)[:3])}")
            
            # Check for parsing failures
            failed_parses = sum(1 for desc in session.content_descriptions 
                              if not desc.parsing_results.get('success'))
            if failed_parses > 0:
                suggestions.append(f"Improve parsing for {failed_parses} files that failed analysis")
        
        return suggestions
    
    def cleanup_session(self, session_id: str, keep_outputs: bool = True):
        """Clean up session data."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        if not keep_outputs:
            # Remove output files
            for file_path in session.output_files.values():
                try:
                    os.remove(file_path)
                except (OSError, FileNotFoundError):
                    pass
        
        # Remove session from memory
        del self.sessions[session_id]
        logger.info(f"Session {session_id} cleaned up")
    
    def export_session_config(self, session_id: str, output_path: str):
        """Export session configuration for reuse."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        config = {
            'session_config': {
                'max_files': session.max_files,
                'structure_type': session.structure_recommendation.structure.name if session.structure_recommendation else None,
                'user_feedback': session.user_feedback
            },
            'processing_instructions': session.structure_recommendation.structure.processing_instructions if session.structure_recommendation else {},
            'vectorization_strategy': session.structure_recommendation.structure.vectorization_strategy if session.structure_recommendation else {}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Session configuration exported to: {output_path}")

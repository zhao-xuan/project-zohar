"""
File Discoverer

Intelligently discovers files in directory structures and decides
which ones to process based on AI analysis of folder patterns,
file names, and content types.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from zohar.utils.logging import get_logger
from zohar.config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class FileInfo:
    """Information about a discovered file."""
    path: str
    name: str
    extension: str
    size: int
    created: float
    modified: float
    parent_dir: str
    depth: int
    is_hidden: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DirectoryPattern:
    """Pattern analysis for a directory."""
    path: str
    file_count: int
    common_extensions: List[str]
    naming_patterns: List[str]
    size_distribution: Dict[str, int]
    creation_timespan: Tuple[float, float]
    similarity_score: float
    

class FileDiscoverer:
    """
    Intelligent file discovery system that analyzes directory structures
    and makes smart decisions about which files to process.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.discovered_files: List[FileInfo] = []
        self.directory_patterns: Dict[str, DirectoryPattern] = {}
        self.file_type_groups: Dict[str, List[FileInfo]] = {}
        
        # Default file type priorities
        self.priority_extensions = {
            'high': {'.txt', '.csv', '.json', '.xml', '.html', '.md', '.log'},
            'medium': {'.pdf', '.docx', '.xlsx', '.pptx', '.odt', '.rtf'},
            'low': {'.jpg', '.png', '.gif', '.mp4', '.mp3', '.zip', '.exe'}
        }
        
        # Extensions to skip by default
        self.skip_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.o', '.obj',
            '.tmp', '.temp', '.cache', '.lock', '.pid', '.swp', '.bak'
        }
        
        # Directories to skip
        self.skip_directories = {
            '__pycache__', '.git', '.svn', '.hg', 'node_modules', '.venv',
            'venv', '.env', 'build', 'dist', '.idea', '.vscode', 'target'
        }
    
    async def discover_files(self, root_path: str, max_files: int = 1000) -> List[FileInfo]:
        """
        Discover files in the given directory with intelligent filtering.
        
        Args:
            root_path: Root directory to scan
            max_files: Maximum number of files to process
            
        Returns:
            List of discovered file information
        """
        logger.info(f"Starting file discovery in: {root_path}")
        
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Invalid directory path: {root_path}")
        
        # First pass: discover all files and analyze patterns
        await self._scan_directory(root, max_depth=5)
        
        # Second pass: analyze patterns and make selection decisions
        await self._analyze_patterns()
        
        # Third pass: intelligent file selection
        selected_files = await self._select_files_intelligently(max_files)
        
        logger.info(f"Discovered {len(self.discovered_files)} files, selected {len(selected_files)} for processing")
        
        return selected_files
    
    async def _scan_directory(self, directory: Path, max_depth: int, current_depth: int = 0):
        """Recursively scan directory and collect file information."""
        if current_depth > max_depth:
            return
            
        if directory.name in self.skip_directories:
            return
        
        try:
            files_in_dir = []
            
            for item in directory.iterdir():
                if item.is_file():
                    file_info = self._create_file_info(item, current_depth)
                    if file_info:
                        self.discovered_files.append(file_info)
                        files_in_dir.append(file_info)
                        
                elif item.is_dir() and not item.name.startswith('.'):
                    await self._scan_directory(item, max_depth, current_depth + 1)
            
            # Analyze patterns for this directory
            if files_in_dir:
                pattern = self._analyze_directory_pattern(directory, files_in_dir)
                self.directory_patterns[str(directory)] = pattern
                
        except PermissionError:
            logger.warning(f"Permission denied accessing: {directory}")
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
    
    def _create_file_info(self, file_path: Path, depth: int) -> Optional[FileInfo]:
        """Create FileInfo object from file path."""
        try:
            stat = file_path.stat()
            extension = file_path.suffix.lower()
            
            # Skip certain file types
            if extension in self.skip_extensions:
                return None
                
            # Skip very large files (> 100MB) for initial discovery
            if stat.st_size > 100 * 1024 * 1024:
                return None
            
            return FileInfo(
                path=str(file_path),
                name=file_path.name,
                extension=extension,
                size=stat.st_size,
                created=stat.st_ctime,
                modified=stat.st_mtime,
                parent_dir=str(file_path.parent),
                depth=depth,
                is_hidden=file_path.name.startswith('.')
            )
            
        except Exception as e:
            logger.error(f"Error creating file info for {file_path}: {e}")
            return None
    
    def _analyze_directory_pattern(self, directory: Path, files: List[FileInfo]) -> DirectoryPattern:
        """Analyze patterns in a directory."""
        if not files:
            return DirectoryPattern(
                path=str(directory),
                file_count=0,
                common_extensions=[],
                naming_patterns=[],
                size_distribution={},
                creation_timespan=(0, 0),
                similarity_score=0.0
            )
        
        # Analyze extensions
        ext_counts = {}
        for file_info in files:
            ext = file_info.extension
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        common_extensions = sorted(ext_counts.keys(), 
                                 key=lambda x: ext_counts[x], reverse=True)[:5]
        
        # Analyze naming patterns
        naming_patterns = self._extract_naming_patterns([f.name for f in files])
        
        # Size distribution
        size_ranges = {'small': 0, 'medium': 0, 'large': 0}
        for file_info in files:
            if file_info.size < 1024 * 1024:  # < 1MB
                size_ranges['small'] += 1
            elif file_info.size < 10 * 1024 * 1024:  # < 10MB
                size_ranges['medium'] += 1
            else:
                size_ranges['large'] += 1
        
        # Creation time span
        creation_times = [f.created for f in files]
        creation_timespan = (min(creation_times), max(creation_times))
        
        # Calculate similarity score
        similarity_score = self._calculate_similarity_score(files)
        
        return DirectoryPattern(
            path=str(directory),
            file_count=len(files),
            common_extensions=common_extensions,
            naming_patterns=naming_patterns,
            size_distribution=size_ranges,
            creation_timespan=creation_timespan,
            similarity_score=similarity_score
        )
    
    def _extract_naming_patterns(self, filenames: List[str]) -> List[str]:
        """Extract common naming patterns from filenames."""
        patterns = []
        
        # Check for date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{8}',              # YYYYMMDD
        ]
        
        # Check for numbering patterns
        number_patterns = [
            r'_\d+\.',             # _001.
            r'\(\d+\)',           # (1)
            r'-\d+\.',            # -001.
        ]
        
        # Check for common prefixes/suffixes
        if len(filenames) > 1:
            common_prefix = os.path.commonprefix(filenames)
            if len(common_prefix) > 3:
                patterns.append(f"prefix:{common_prefix}")
        
        return patterns[:3]  # Return top 3 patterns
    
    def _calculate_similarity_score(self, files: List[FileInfo]) -> float:
        """Calculate how similar files in a directory are."""
        if len(files) < 2:
            return 0.0
        
        # Check extension uniformity
        extensions = [f.extension for f in files]
        ext_uniformity = len(set(extensions)) / len(extensions)
        
        # Check size uniformity
        sizes = [f.size for f in files]
        avg_size = sum(sizes) / len(sizes)
        size_variance = sum((s - avg_size) ** 2 for s in sizes) / len(sizes)
        size_uniformity = 1.0 / (1.0 + size_variance / (avg_size + 1))
        
        # Check creation time clustering
        creation_times = [f.created for f in files]
        time_span = max(creation_times) - min(creation_times)
        time_uniformity = 1.0 / (1.0 + time_span / 86400)  # Days
        
        # Combined similarity score
        return (ext_uniformity + size_uniformity + time_uniformity) / 3
    
    async def _analyze_patterns(self):
        """Analyze discovered patterns and group files."""
        # Group files by extension
        for file_info in self.discovered_files:
            ext = file_info.extension
            if ext not in self.file_type_groups:
                self.file_type_groups[ext] = []
            self.file_type_groups[ext].append(file_info)
        
        logger.info(f"Found file types: {list(self.file_type_groups.keys())}")
    
    async def _select_files_intelligently(self, max_files: int) -> List[FileInfo]:
        """Intelligently select files for processing."""
        selected_files = []
        files_by_priority = {'high': [], 'medium': [], 'low': []}
        
        # Categorize files by priority
        for file_info in self.discovered_files:
            ext = file_info.extension
            
            if ext in self.priority_extensions['high']:
                files_by_priority['high'].append(file_info)
            elif ext in self.priority_extensions['medium']:
                files_by_priority['medium'].append(file_info)
            else:
                files_by_priority['low'].append(file_info)
        
        # Select files starting with high priority
        remaining_quota = max_files
        
        for priority in ['high', 'medium', 'low']:
            candidates = files_by_priority[priority]
            
            if not candidates or remaining_quota <= 0:
                continue
            
            # For similar files, limit the number processed
            selected_from_priority = self._apply_similarity_limits(candidates, remaining_quota)
            selected_files.extend(selected_from_priority)
            remaining_quota -= len(selected_from_priority)
        
        return selected_files[:max_files]
    
    def _apply_similarity_limits(self, files: List[FileInfo], max_count: int) -> List[FileInfo]:
        """Apply similarity-based limits to file selection."""
        if not files:
            return []
        
        # Group by directory and extension
        groups = {}
        for file_info in files:
            key = (file_info.parent_dir, file_info.extension)
            if key not in groups:
                groups[key] = []
            groups[key].append(file_info)
        
        selected = []
        
        for (parent_dir, extension), group_files in groups.items():
            # Check if this directory has high similarity
            dir_pattern = self.directory_patterns.get(parent_dir)
            
            if dir_pattern and dir_pattern.similarity_score > 0.8 and len(group_files) > 5:
                # High similarity - limit to representative samples
                limit = min(3, len(group_files))
                # Select first, middle, and last files as representatives
                indices = [0, len(group_files) // 2, len(group_files) - 1]
                for i in indices[:limit]:
                    if len(selected) < max_count:
                        selected.append(group_files[i])
            else:
                # Normal selection
                for file_info in group_files:
                    if len(selected) < max_count:
                        selected.append(file_info)
        
        return selected
    
    def save_discovery_results(self, output_path: str):
        """Save discovery results to JSON file."""
        results = {
            'discovery_timestamp': datetime.now().isoformat(),
            'total_files_discovered': len(self.discovered_files),
            'directory_patterns': {k: asdict(v) for k, v in self.directory_patterns.items()},
            'file_type_distribution': {k: len(v) for k, v in self.file_type_groups.items()},
            'discovered_files': [f.to_dict() for f in self.discovered_files]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Discovery results saved to: {output_path}")
    
    def get_discovery_summary(self) -> Dict:
        """Get a summary of the discovery process."""
        return {
            'total_files': len(self.discovered_files),
            'directories_analyzed': len(self.directory_patterns),
            'file_types': list(self.file_type_groups.keys()),
            'largest_directory': max(self.directory_patterns.values(), 
                                   key=lambda x: x.file_count, default=None),
            'most_similar_directory': max(self.directory_patterns.values(),
                                        key=lambda x: x.similarity_score, default=None)
        } 
"""
Format Detector

Advanced file format detection using multiple methods including
magic bytes, file headers, content analysis, and encoding detection.
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

from zohar.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FormatInfo:
    """Information about detected file format."""
    file_path: str
    detected_format: str
    mime_type: str
    encoding: str
    confidence: float
    is_text: bool
    is_binary: bool
    magic_signature: Optional[str]
    header_bytes: bytes
    estimated_format: str
    format_confidence: float


class FormatDetector:
    """
    Advanced format detection using multiple approaches:
    1. Magic bytes detection
    2. File extension analysis
    3. Content sniffing
    4. Encoding detection
    5. MIME type detection
    """
    
    def __init__(self):
        # Initialize magic if available
        self.magic_mime = None
        self.magic_type = None
        
        if HAS_MAGIC:
            try:
                self.magic_mime = magic.Magic(mime=True)
                self.magic_type = magic.Magic()
            except Exception as e:
                logger.warning(f"Failed to initialize python-magic: {e}")
        
        # Common file signatures (magic bytes)
        self.magic_signatures = {
            b'\x50\x4B\x03\x04': 'zip',
            b'\x50\x4B\x05\x06': 'zip_empty',
            b'\x50\x4B\x07\x08': 'zip_spanned',
            b'\x52\x61\x72\x21': 'rar',
            b'\x7F\x45\x4C\x46': 'elf',
            b'\x89\x50\x4E\x47': 'png',
            b'\xFF\xD8\xFF': 'jpeg',
            b'\x47\x49\x46\x38': 'gif',
            b'\x25\x50\x44\x46': 'pdf',
            b'\xD0\xCF\x11\xE0': 'ole2',  # MS Office old format
            b'\x1F\x8B\x08': 'gzip',
            b'\x42\x5A\x68': 'bzip2',
            b'\xFD\x37\x7A\x58\x5A\x00': 'xz',
            b'\x37\x7A\xBC\xAF\x27\x1C': '7z',
            b'\x4D\x5A': 'pe_executable',
            b'\x7F\x45\x4C\x46': 'elf_executable',
            b'\xCA\xFE\xBA\xBE': 'java_class',
            b'\xEF\xBB\xBF': 'utf8_bom',
            b'\xFF\xFE': 'utf16_le_bom',
            b'\xFE\xFF': 'utf16_be_bom',
        }
        
        # Text file indicators
        self.text_extensions = {
            '.txt', '.csv', '.json', '.xml', '.html', '.htm', '.md', 
            '.log', '.conf', '.cfg', '.ini', '.yaml', '.yml', '.py',
            '.js', '.css', '.sql', '.sh', '.bat', '.ps1', '.r', '.m',
            '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.php'
        }
        
        # Binary file indicators  
        self.binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db',
            '.sqlite', '.img', '.iso', '.dmg', '.pkg', '.msi', '.deb',
            '.rpm', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
        }
    
    def detect_format(self, file_path: str, read_bytes: int = 8192) -> FormatInfo:
        """
        Detect file format using multiple methods.
        
        Args:
            file_path: Path to the file
            read_bytes: Number of bytes to read for analysis
            
        Returns:
            FormatInfo with detection results
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file header
        try:
            with open(file_path, 'rb') as f:
                header_bytes = f.read(read_bytes)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            header_bytes = b''
        
        # Detect using multiple methods
        mime_type = self._detect_mime_type(file_path)
        magic_info = self._detect_magic_signature(header_bytes)
        encoding_info = self._detect_encoding(file_path, header_bytes)
        format_from_extension = self._detect_from_extension(path.suffix.lower())
        format_from_content = self._detect_from_content(header_bytes)
        
        # Determine if file is text or binary
        is_text, is_binary = self._determine_text_binary(
            path.suffix.lower(), header_bytes, encoding_info['encoding']
        )
        
        # Combine results and determine best format guess
        detected_format, confidence = self._combine_detection_results(
            magic_info, format_from_extension, format_from_content, mime_type
        )
        
        return FormatInfo(
            file_path=file_path,
            detected_format=detected_format,
            mime_type=mime_type,
            encoding=encoding_info['encoding'],
            confidence=encoding_info['confidence'],
            is_text=is_text,
            is_binary=is_binary,
            magic_signature=magic_info['signature'],
            header_bytes=header_bytes[:64],  # Store first 64 bytes
            estimated_format=detected_format,
            format_confidence=confidence
        )
    
    def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type using multiple methods."""
        # Try mimetypes module first
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type:
            return mime_type
        
        # Try python-magic if available
        if self.magic_mime:
            try:
                return self.magic_mime.from_file(file_path)
            except Exception as e:
                logger.debug(f"Magic MIME detection failed: {e}")
        
        return 'application/octet-stream'
    
    def _detect_magic_signature(self, header_bytes: bytes) -> Dict[str, Any]:
        """Detect format from magic bytes signature."""
        result = {'signature': None, 'format': None, 'confidence': 0.0}
        
        if not header_bytes:
            return result
        
        # Check known magic signatures
        for signature, format_name in self.magic_signatures.items():
            if header_bytes.startswith(signature):
                result['signature'] = signature.hex()
                result['format'] = format_name
                result['confidence'] = 0.9
                return result
        
        # Try python-magic if available
        if self.magic_type:
            try:
                magic_result = self.magic_type.from_buffer(header_bytes)
                result['signature'] = magic_result
                result['confidence'] = 0.7
                # Extract format from magic description
                result['format'] = self._parse_magic_description(magic_result)
            except Exception as e:
                logger.debug(f"Magic detection failed: {e}")
        
        return result
    
    def _detect_encoding(self, file_path: str, header_bytes: bytes) -> Dict[str, Any]:
        """Detect text encoding."""
        result = {'encoding': 'unknown', 'confidence': 0.0}
        
        # Check for BOM
        if header_bytes.startswith(b'\xEF\xBB\xBF'):
            return {'encoding': 'utf-8-sig', 'confidence': 1.0}
        elif header_bytes.startswith(b'\xFF\xFE'):
            return {'encoding': 'utf-16-le', 'confidence': 1.0}
        elif header_bytes.startswith(b'\xFE\xFF'):
            return {'encoding': 'utf-16-be', 'confidence': 1.0}
        
        # Try chardet if available
        if HAS_CHARDET and header_bytes:
            try:
                detection = chardet.detect(header_bytes)
                if detection and detection['encoding']:
                    return {
                        'encoding': detection['encoding'].lower(),
                        'confidence': detection['confidence']
                    }
            except Exception as e:
                logger.debug(f"Chardet detection failed: {e}")
        
        # Fallback: try common encodings
        for encoding in ['utf-8', 'ascii', 'latin-1', 'cp1252']:
            try:
                header_bytes.decode(encoding)
                result['encoding'] = encoding
                result['confidence'] = 0.5 if encoding == 'utf-8' else 0.3
                break
            except UnicodeDecodeError:
                continue
        
        return result
    
    def _detect_from_extension(self, extension: str) -> Optional[str]:
        """Detect format from file extension."""
        extension_map = {
            '.txt': 'text',
            '.csv': 'csv',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.htm': 'html',
            '.md': 'markdown',
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.xlsx': 'xlsx',
            '.pptx': 'pptx',
            '.zip': 'zip',
            '.rar': 'rar',
            '.7z': '7z',
            '.tar': 'tar',
            '.gz': 'gzip',
            '.bz2': 'bzip2',
            '.xz': 'xz',
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.png': 'png',
            '.gif': 'gif',
            '.bmp': 'bmp',
            '.tiff': 'tiff',
            '.mp3': 'mp3',
            '.mp4': 'mp4',
            '.avi': 'avi',
            '.wav': 'wav',
            '.exe': 'executable',
            '.dll': 'dll',
            '.so': 'shared_library',
            '.dylib': 'shared_library',
            '.db': 'database',
            '.sqlite': 'sqlite',
            '.log': 'log',
            '.conf': 'config',
            '.cfg': 'config',
            '.ini': 'config',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.py': 'python',
            '.js': 'javascript',
            '.css': 'css',
            '.sql': 'sql',
        }
        
        return extension_map.get(extension)
    
    def _detect_from_content(self, header_bytes: bytes) -> Optional[str]:
        """Detect format from content analysis."""
        if not header_bytes:
            return None
        
        # Try to decode as text
        try:
            text_content = header_bytes.decode('utf-8', errors='ignore')
            
            # JSON detection
            if text_content.strip().startswith(('{', '[')):
                return 'json'
            
            # XML detection
            if text_content.strip().startswith('<?xml') or text_content.strip().startswith('<'):
                return 'xml'
            
            # CSV detection (basic)
            lines = text_content.strip().split('\n')[:5]
            if len(lines) > 1:
                # Check if multiple lines have consistent comma separation
                comma_counts = [line.count(',') for line in lines if line.strip()]
                if len(set(comma_counts)) <= 2 and all(c > 0 for c in comma_counts):
                    return 'csv'
            
            # Log file detection
            if any(pattern in text_content.lower() for pattern in 
                   ['error', 'warning', 'info', 'debug', 'timestamp', 'log']):
                return 'log'
                
        except UnicodeDecodeError:
            pass
        
        # Binary format detection
        if header_bytes.startswith(b'%PDF'):
            return 'pdf'
        elif header_bytes.startswith(b'GIF8'):
            return 'gif'
        elif header_bytes.startswith(b'\x89PNG'):
            return 'png'
        elif header_bytes.startswith(b'\xFF\xD8\xFF'):
            return 'jpeg'
        
        return None
    
    def _determine_text_binary(self, extension: str, header_bytes: bytes, encoding: str) -> Tuple[bool, bool]:
        """Determine if file is text or binary."""
        # Check extension first
        if extension in self.text_extensions:
            return True, False
        elif extension in self.binary_extensions:
            return False, True
        
        # Check encoding confidence
        if encoding != 'unknown' and encoding != 'binary':
            # Try to decode a portion as text
            try:
                if header_bytes:
                    decoded = header_bytes.decode(encoding, errors='strict')
                    # Check for non-printable characters
                    printable_ratio = sum(1 for c in decoded if c.isprintable() or c.isspace()) / len(decoded)
                    if printable_ratio > 0.7:
                        return True, False
            except UnicodeDecodeError:
                pass
        
        # Check for null bytes (strong binary indicator)
        if b'\x00' in header_bytes[:1024]:
            return False, True
        
        # Default: assume text if reasonable encoding detected
        if encoding in ['utf-8', 'ascii', 'latin-1']:
            return True, False
        
        return False, True
    
    def _combine_detection_results(self, magic_info: Dict, ext_format: Optional[str], 
                                 content_format: Optional[str], mime_type: str) -> Tuple[str, float]:
        """Combine detection results and determine best guess."""
        candidates = []
        
        # Magic signature (highest confidence)
        if magic_info['format']:
            candidates.append((magic_info['format'], magic_info['confidence']))
        
        # Content analysis (high confidence for text formats)
        if content_format:
            confidence = 0.8 if content_format in ['json', 'xml', 'csv'] else 0.6
            candidates.append((content_format, confidence))
        
        # Extension (medium confidence)
        if ext_format:
            candidates.append((ext_format, 0.5))
        
        # MIME type (low confidence for generic types)
        if mime_type and mime_type != 'application/octet-stream':
            mime_format = mime_type.split('/')[-1]
            candidates.append((mime_format, 0.3))
        
        if not candidates:
            return 'unknown', 0.0
        
        # Return highest confidence result
        best_format, best_confidence = max(candidates, key=lambda x: x[1])
        return best_format, best_confidence
    
    def _parse_magic_description(self, magic_description: str) -> str:
        """Parse magic library description to extract format."""
        description = magic_description.lower()
        
        format_keywords = {
            'pdf': 'pdf',
            'zip': 'zip',
            'gzip': 'gzip',
            'jpeg': 'jpeg',
            'png': 'png',
            'gif': 'gif',
            'html': 'html',
            'xml': 'xml',
            'json': 'json',
            'text': 'text',
            'executable': 'executable',
            'archive': 'archive',
            'image': 'image',
            'audio': 'audio',
            'video': 'video'
        }
        
        for keyword, format_name in format_keywords.items():
            if keyword in description:
                return format_name
        
        return 'unknown'
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported format detection."""
        return list(set(
            list(self.magic_signatures.values()) +
            [v for v in self._detect_from_extension.__defaults__[0].values() if v] +
            ['json', 'xml', 'csv', 'log', 'pdf', 'gif', 'png', 'jpeg']
        ))
    
    def batch_detect(self, file_paths: List[str]) -> Dict[str, FormatInfo]:
        """Detect formats for multiple files."""
        results = {}
        
        for file_path in file_paths:
            try:
                results[file_path] = self.detect_format(file_path)
            except Exception as e:
                logger.error(f"Failed to detect format for {file_path}: {e}")
                # Create basic FormatInfo for failed detection
                results[file_path] = FormatInfo(
                    file_path=file_path,
                    detected_format='unknown',
                    mime_type='application/octet-stream',
                    encoding='unknown',
                    confidence=0.0,
                    is_text=False,
                    is_binary=True,
                    magic_signature=None,
                    header_bytes=b'',
                    estimated_format='unknown',
                    format_confidence=0.0
                )
        
        return results 
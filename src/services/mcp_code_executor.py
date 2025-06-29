#!/usr/bin/env python3
"""
MCP Code Execution Server

Provides secure code execution and file system operations for AI agents.
Allows agents to create files, run Python code, manage directories, etc.
"""

import asyncio
import os
import subprocess
import tempfile
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import ast
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPCodeExecutor:
    """
    MCP Code Execution Server for running code and file operations
    """
    
    def __init__(self, workspace_path: str = None, sandbox_mode: bool = True):
        """
        Initialize the code executor
        
        Args:
            workspace_path: Base workspace directory
            sandbox_mode: Whether to run in sandboxed mode
        """
        if workspace_path is None:
            workspace_path = os.path.join(os.getcwd(), "agent_workspace")
        
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        self.sandbox_mode = sandbox_mode
        self.execution_history = []
        
        # Allowed imports for security
        self.allowed_imports = {
            'os', 'sys', 'json', 'csv', 'datetime', 'time', 'math', 'random',
            'pathlib', 're', 'collections', 'itertools', 'functools',
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'requests', 'urllib',
            'beautifulsoup4', 'lxml', 'sqlite3', 'logging',
            'chromadb', 'pickle', 'joblib', 'sklearn'
        }
        
        logger.info(f"Initialized code executor with workspace: {self.workspace_path}")
    
    async def create_file(self, file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a file with specified content
        
        Args:
            file_path: Path to the file (relative to workspace)
            content: File content
            overwrite: Whether to overwrite existing files
            
        Returns:
            Operation result
        """
        try:
            # Ensure path is within workspace
            full_path = self._resolve_path(file_path)
            
            if full_path.exists() and not overwrite:
                return {
                    'success': False,
                    'error': f'File {file_path} already exists. Use overwrite=True to replace it.'
                }
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'file_path': str(full_path),
                'size': len(content),
                'message': f'File created: {file_path}'
            }
            
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read content from a file
        
        Args:
            file_path: Path to the file (relative to workspace)
            
        Returns:
            File content and metadata
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                return {
                    'success': False,
                    'error': f'File {file_path} does not exist'
                }
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'success': True,
                'file_path': str(full_path),
                'content': content,
                'size': len(content),
                'modified_time': datetime.fromtimestamp(full_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        Create a directory
        
        Args:
            dir_path: Path to the directory (relative to workspace)
            
        Returns:
            Operation result
        """
        try:
            full_path = self._resolve_path(dir_path)
            full_path.mkdir(parents=True, exist_ok=True)
            
            return {
                'success': True,
                'directory_path': str(full_path),
                'message': f'Directory created: {dir_path}'
            }
            
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """
        List contents of a directory
        
        Args:
            dir_path: Path to the directory (relative to workspace)
            
        Returns:
            Directory contents
        """
        try:
            full_path = self._resolve_path(dir_path)
            
            if not full_path.exists():
                return {
                    'success': False,
                    'error': f'Directory {dir_path} does not exist'
                }
            
            if not full_path.is_dir():
                return {
                    'success': False,
                    'error': f'{dir_path} is not a directory'
                }
            
            contents = []
            for item in full_path.iterdir():
                item_info = {
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else 0,
                    'modified_time': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                contents.append(item_info)
            
            return {
                'success': True,
                'directory_path': str(full_path),
                'contents': contents,
                'total_items': len(contents)
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {dir_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_python_code(self, code: str, timeout: int = 30, 
                                 capture_output: bool = True) -> Dict[str, Any]:
        """
        Execute Python code in a controlled environment
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Execution result
        """
        try:
            # Validate code safety in sandbox mode
            if self.sandbox_mode and not self._validate_code_safety(code):
                return {
                    'success': False,
                    'error': 'Code contains potentially unsafe operations'
                }
            
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
                tmp_file.write(code)
                tmp_file_path = tmp_file.name
            
            try:
                # Execute the code
                if capture_output:
                    result = subprocess.run(
                        [sys.executable, tmp_file_path],
                        cwd=str(self.workspace_path),
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                    execution_result = {
                        'success': result.returncode == 0,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode,
                        'execution_time': timeout  # Approximate
                    }
                else:
                    result = subprocess.run(
                        [sys.executable, tmp_file_path],
                        cwd=str(self.workspace_path),
                        timeout=timeout
                    )
                    
                    execution_result = {
                        'success': result.returncode == 0,
                        'return_code': result.returncode,
                        'execution_time': timeout  # Approximate
                    }
                
                # Record execution history
                self.execution_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'code': code[:500] + '...' if len(code) > 500 else code,
                    'success': execution_result['success'],
                    'return_code': execution_result['return_code']
                })
                
                return execution_result
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Code execution timed out after {timeout} seconds'
            }
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_shell_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a shell command
        
        Args:
            command: Shell command to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Command execution result
        """
        try:
            # Security check for dangerous commands
            if self.sandbox_mode and self._is_dangerous_command(command):
                return {
                    'success': False,
                    'error': 'Command contains potentially dangerous operations'
                }
            
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'command': command
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Command timed out after {timeout} seconds'
            }
        except Exception as e:
            logger.error(f"Error executing shell command: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def install_package(self, package_name: str) -> Dict[str, Any]:
        """
        Install a Python package using pip
        
        Args:
            package_name: Name of the package to install
            
        Returns:
            Installation result
        """
        try:
            # Security check - only allow known safe packages
            if self.sandbox_mode:
                safe_packages = {
                    'numpy', 'pandas', 'matplotlib', 'seaborn', 'requests', 
                    'beautifulsoup4', 'lxml', 'scikit-learn', 'scipy',
                    'plotly', 'dash', 'streamlit', 'fastapi', 'flask',
                    'chromadb', 'sentence-transformers', 'transformers',
                    'pillow', 'opencv-python', 'pytesseract', 'pymupdf',
                    'python-docx', 'openpyxl', 'python-pptx'
                }
                
                if package_name.lower() not in safe_packages:
                    return {
                        'success': False,
                        'error': f'Package {package_name} is not in the allowed list'
                    }
            
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'package': package_name,
                'message': f'Package {package_name} installation completed'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Package installation timed out'
            }
        except Exception as e:
            logger.error(f"Error installing package {package_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def copy_file(self, source_path: str, dest_path: str) -> Dict[str, Any]:
        """
        Copy a file
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            Operation result
        """
        try:
            source_full = self._resolve_path(source_path)
            dest_full = self._resolve_path(dest_path)
            
            if not source_full.exists():
                return {
                    'success': False,
                    'error': f'Source file {source_path} does not exist'
                }
            
            # Create destination directory if needed
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_full, dest_full)
            
            return {
                'success': True,
                'source': str(source_full),
                'destination': str(dest_full),
                'message': f'File copied from {source_path} to {dest_path}'
            }
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            Operation result
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                return {
                    'success': False,
                    'error': f'File {file_path} does not exist'
                }
            
            if full_path.is_dir():
                shutil.rmtree(full_path)
                message = f'Directory {file_path} deleted'
            else:
                full_path.unlink()
                message = f'File {file_path} deleted'
            
            return {
                'success': True,
                'deleted_path': str(full_path),
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_workspace_info(self) -> Dict[str, Any]:
        """
        Get information about the workspace
        
        Returns:
            Workspace information
        """
        try:
            total_files = 0
            total_size = 0
            
            for root, dirs, files in os.walk(self.workspace_path):
                total_files += len(files)
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
            
            return {
                'success': True,
                'workspace_path': str(self.workspace_path),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'sandbox_mode': self.sandbox_mode,
                'execution_history_count': len(self.execution_history)
            }
            
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to the workspace
        
        Args:
            path: Relative path
            
        Returns:
            Absolute path within workspace
        """
        # Ensure path is relative and within workspace
        path = Path(path)
        
        if path.is_absolute():
            raise ValueError("Absolute paths are not allowed")
        
        # Resolve relative to workspace
        full_path = (self.workspace_path / path).resolve()
        
        # Ensure the resolved path is still within workspace
        try:
            full_path.relative_to(self.workspace_path.resolve())
        except ValueError:
            raise ValueError("Path traversal outside workspace is not allowed")
        
        return full_path
    
    def _validate_code_safety(self, code: str) -> bool:
        """
        Validate that code is safe to execute
        
        Args:
            code: Python code to validate
            
        Returns:
            True if code appears safe
        """
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Check for dangerous operations
            for node in ast.walk(tree):
                # Check for dangerous imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_imports:
                            logger.warning(f"Blocked import: {alias.name}")
                            return False
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_imports:
                        logger.warning(f"Blocked import from: {node.module}")
                        return False
                
                # Check for dangerous function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        dangerous_functions = {'eval', 'exec', 'compile', '__import__'}
                        if node.func.id in dangerous_functions:
                            logger.warning(f"Blocked dangerous function: {node.func.id}")
                            return False
                
                # Check for file operations outside workspace
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id == 'os':
                        dangerous_attrs = {'system', 'popen', 'spawn'}
                        if node.attr in dangerous_attrs:
                            logger.warning(f"Blocked dangerous os operation: {node.attr}")
                            return False
            
            return True
            
        except SyntaxError:
            logger.warning("Code has syntax errors")
            return False
        except Exception as e:
            logger.warning(f"Error validating code: {e}")
            return False
    
    def _is_dangerous_command(self, command: str) -> bool:
        """
        Check if a shell command is potentially dangerous
        
        Args:
            command: Shell command
            
        Returns:
            True if command is dangerous
        """
        dangerous_patterns = [
            'rm -rf', 'rm -r /', 'format', 'del /s',
            'shutdown', 'reboot', 'halt',
            'chmod 777', 'chown root',
            'wget', 'curl', 'nc ', 'netcat',
            'sudo', 'su -', 'passwd',
            'iptables', 'ufw', 'firewall'
        ]
        
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return True
        
        return False
    
    # MCP Protocol Implementation
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Return MCP tool definitions"""
        return [
            {
                'name': 'create_file',
                'description': 'Create a file with specified content',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string', 'description': 'Path to the file (relative to workspace)'},
                        'content': {'type': 'string', 'description': 'File content'},
                        'overwrite': {'type': 'boolean', 'default': False, 'description': 'Whether to overwrite existing files'}
                    },
                    'required': ['file_path', 'content']
                }
            },
            {
                'name': 'read_file',
                'description': 'Read content from a file',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string', 'description': 'Path to the file (relative to workspace)'}
                    },
                    'required': ['file_path']
                }
            },
            {
                'name': 'create_directory',
                'description': 'Create a directory',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'dir_path': {'type': 'string', 'description': 'Path to the directory (relative to workspace)'}
                    },
                    'required': ['dir_path']
                }
            },
            {
                'name': 'list_directory',
                'description': 'List contents of a directory',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'dir_path': {'type': 'string', 'default': '.', 'description': 'Path to the directory (relative to workspace)'}
                    }
                }
            },
            {
                'name': 'execute_python_code',
                'description': 'Execute Python code in a controlled environment',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'code': {'type': 'string', 'description': 'Python code to execute'},
                        'timeout': {'type': 'integer', 'default': 30, 'description': 'Maximum execution time in seconds'},
                        'capture_output': {'type': 'boolean', 'default': True, 'description': 'Whether to capture stdout/stderr'}
                    },
                    'required': ['code']
                }
            },
            {
                'name': 'execute_shell_command',
                'description': 'Execute a shell command',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'command': {'type': 'string', 'description': 'Shell command to execute'},
                        'timeout': {'type': 'integer', 'default': 30, 'description': 'Maximum execution time in seconds'}
                    },
                    'required': ['command']
                }
            },
            {
                'name': 'install_package',
                'description': 'Install a Python package using pip',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'package_name': {'type': 'string', 'description': 'Name of the package to install'}
                    },
                    'required': ['package_name']
                }
            },
            {
                'name': 'copy_file',
                'description': 'Copy a file',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'source_path': {'type': 'string', 'description': 'Source file path'},
                        'dest_path': {'type': 'string', 'description': 'Destination file path'}
                    },
                    'required': ['source_path', 'dest_path']
                }
            },
            {
                'name': 'delete_file',
                'description': 'Delete a file or directory',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string', 'description': 'Path to the file to delete'}
                    },
                    'required': ['file_path']
                }
            },
            {
                'name': 'get_workspace_info',
                'description': 'Get information about the workspace',
                'parameters': {
                    'type': 'object',
                    'properties': {}
                }
            }
        ]
    
    async def handle_mcp_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool calls"""
        try:
            if tool_name == 'create_file':
                return await self.create_file(
                    parameters['file_path'],
                    parameters['content'],
                    parameters.get('overwrite', False)
                )
            elif tool_name == 'read_file':
                return await self.read_file(parameters['file_path'])
            elif tool_name == 'create_directory':
                return await self.create_directory(parameters['dir_path'])
            elif tool_name == 'list_directory':
                return await self.list_directory(parameters.get('dir_path', '.'))
            elif tool_name == 'execute_python_code':
                return await self.execute_python_code(
                    parameters['code'],
                    parameters.get('timeout', 30),
                    parameters.get('capture_output', True)
                )
            elif tool_name == 'execute_shell_command':
                return await self.execute_shell_command(
                    parameters['command'],
                    parameters.get('timeout', 30)
                )
            elif tool_name == 'install_package':
                return await self.install_package(parameters['package_name'])
            elif tool_name == 'copy_file':
                return await self.copy_file(
                    parameters['source_path'],
                    parameters['dest_path']
                )
            elif tool_name == 'delete_file':
                return await self.delete_file(parameters['file_path'])
            elif tool_name == 'get_workspace_info':
                return await self.get_workspace_info()
            else:
                return {'success': False, 'error': f'Unknown tool: {tool_name}'}
                
        except KeyError as e:
            return {'success': False, 'error': f'Missing required parameter: {e}'}
        except Exception as e:
            logger.error(f"Error handling MCP call {tool_name}: {e}")
            return {'success': False, 'error': str(e)}

async def main():
    """Main function to run the MCP Code Execution Server"""
    executor = MCPCodeExecutor()
    
    logger.info("MCP Code Execution Server is ready!")
    logger.info(f"Workspace: {executor.workspace_path}")
    logger.info(f"Sandbox mode: {executor.sandbox_mode}")
    logger.info(f"Available tools: {[tool['name'] for tool in executor.get_mcp_tools()]}")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
File Security Validation Module
Provides comprehensive file and directory security validation for the AI Chief of Staff system.

Security Features:
- File permission validation
- Directory security checks
- Path traversal prevention
- Ownership verification
- Secure file creation
"""

import os
import stat
import pwd
import grp
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different file types"""
    PUBLIC = "public"           # 644 - readable by all
    RESTRICTED = "restricted"   # 640 - readable by group
    PRIVATE = "private"         # 600 - owner only
    SECRET = "secret"           # 600 with additional checks


@dataclass
class SecurityRequirements:
    """Security requirements for a file or directory"""
    level: SecurityLevel
    required_permissions: int
    owner_only: bool = False
    group_readable: bool = False
    world_readable: bool = False
    must_be_directory: bool = False
    parent_directory_secure: bool = True
    

class FileSecurityValidator:
    """Comprehensive file security validation system"""
    
    # Security profiles for different file types
    SECURITY_PROFILES = {
        'master_key': SecurityRequirements(
            level=SecurityLevel.SECRET,
            required_permissions=0o600,
            owner_only=True,
            parent_directory_secure=True
        ),
        'encrypted_db': SecurityRequirements(
            level=SecurityLevel.PRIVATE,
            required_permissions=0o600,
            owner_only=True,
            parent_directory_secure=True
        ),
        'config_file': SecurityRequirements(
            level=SecurityLevel.RESTRICTED,
            required_permissions=0o640,
            owner_only=True,
            group_readable=True
        ),
        'log_file': SecurityRequirements(
            level=SecurityLevel.RESTRICTED,
            required_permissions=0o640,
            owner_only=True,
            group_readable=True
        ),
        'data_directory': SecurityRequirements(
            level=SecurityLevel.PRIVATE,
            required_permissions=0o700,
            owner_only=True,
            must_be_directory=True,
            parent_directory_secure=True
        ),
        'temp_directory': SecurityRequirements(
            level=SecurityLevel.PRIVATE,
            required_permissions=0o700,
            owner_only=True,
            must_be_directory=True
        )
    }
    
    def __init__(self):
        self.current_user = pwd.getpwuid(os.getuid())
        self.current_group = grp.getgrgid(os.getgid())
        
    def validate_file_security(self, file_path: str, profile: str = 'config_file') -> Dict[str, Any]:
        """
        Comprehensive security validation for a file
        
        Args:
            file_path: Path to validate
            profile: Security profile to use
            
        Returns:
            Validation result with security status and issues
        """
        path = Path(file_path).resolve()
        
        if profile not in self.SECURITY_PROFILES:
            return {
                'valid': False,
                'error': f'Unknown security profile: {profile}',
                'issues': [f'Security profile "{profile}" not defined']
            }
            
        requirements = self.SECURITY_PROFILES[profile]
        
        try:
            issues = []
            warnings = []
            
            # Check if path exists
            if not path.exists():
                return {
                    'valid': False,
                    'error': f'Path does not exist: {path}',
                    'issues': ['File or directory not found'],
                    'can_create': self._can_create_securely(path, requirements)
                }
            
            # Get file stats
            stat_info = path.stat()
            
            # Validate file type
            if requirements.must_be_directory and not path.is_dir():
                issues.append(f'Expected directory but found file: {path}')
            elif not requirements.must_be_directory and path.is_dir():
                warnings.append(f'Expected file but found directory: {path}')
            
            # Validate permissions
            current_perms = stat.S_IMODE(stat_info.st_mode)
            if current_perms != requirements.required_permissions:
                issues.append(
                    f'Incorrect permissions: {oct(current_perms)} '
                    f'(expected {oct(requirements.required_permissions)})'
                )
            
            # Validate ownership
            if stat_info.st_uid != os.getuid():
                issues.append(
                    f'File not owned by current user: {stat_info.st_uid} '
                    f'(expected {os.getuid()})'
                )
            
            # Check for world-writable permissions (major security risk)
            if current_perms & stat.S_IWOTH:
                issues.append('File is world-writable - major security risk')
            
            # Check parent directory security if required
            if requirements.parent_directory_secure:
                parent_issues = self._validate_parent_security(path.parent)
                issues.extend(parent_issues)
            
            # Check for symbolic links (potential security issue)
            if path.is_symlink():
                warnings.append('File is a symbolic link - verify target security')
            
            # Additional checks for secret files
            if requirements.level == SecurityLevel.SECRET:
                secret_issues = self._validate_secret_file(path)
                issues.extend(secret_issues)
            
            return {
                'valid': len(issues) == 0,
                'path': str(path),
                'issues': issues,
                'warnings': warnings,
                'current_permissions': oct(current_perms),
                'required_permissions': oct(requirements.required_permissions),
                'owner': self._get_owner_info(stat_info),
                'security_level': requirements.level.value
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Security validation failed: {str(e)}',
                'path': str(path),
                'issues': [f'Validation error: {str(e)}']
            }
    
    def create_secure_file(self, file_path: str, profile: str = 'config_file', 
                          content: str = None) -> Dict[str, Any]:
        """
        Create a file with secure permissions
        
        Args:
            file_path: Path to create
            profile: Security profile to use
            content: Optional initial content
            
        Returns:
            Creation result
        """
        path = Path(file_path).resolve()
        
        if profile not in self.SECURITY_PROFILES:
            return {
                'success': False,
                'error': f'Unknown security profile: {profile}'
            }
            
        requirements = self.SECURITY_PROFILES[profile]
        
        try:
            # Validate parent directory security
            if not path.parent.exists():
                # Create parent directories securely
                path.parent.mkdir(parents=True, mode=0o700)
            
            if requirements.parent_directory_secure:
                parent_issues = self._validate_parent_security(path.parent)
                if parent_issues:
                    return {
                        'success': False,
                        'error': 'Parent directory security issues',
                        'issues': parent_issues
                    }
            
            # Create file or directory with secure permissions
            if requirements.must_be_directory:
                path.mkdir(mode=requirements.required_permissions, exist_ok=True)
            else:
                # Create file with restrictive permissions first
                with open(path, 'w') as f:
                    if content:
                        f.write(content)
                
                # Set correct permissions
                os.chmod(path, requirements.required_permissions)
            
            # Verify security after creation
            validation_result = self.validate_file_security(str(path), profile)
            
            return {
                'success': validation_result['valid'],
                'path': str(path),
                'validation': validation_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create secure file: {str(e)}',
                'path': str(path)
            }
    
    def fix_file_permissions(self, file_path: str, profile: str) -> Dict[str, Any]:
        """
        Fix file permissions to match security requirements
        
        Args:
            file_path: Path to fix
            profile: Security profile to apply
            
        Returns:
            Fix result
        """
        path = Path(file_path).resolve()
        
        if profile not in self.SECURITY_PROFILES:
            return {
                'success': False,
                'error': f'Unknown security profile: {profile}'
            }
            
        requirements = self.SECURITY_PROFILES[profile]
        
        try:
            if not path.exists():
                return {
                    'success': False,
                    'error': f'File does not exist: {path}'
                }
            
            # Get current permissions
            current_perms = stat.S_IMODE(path.stat().st_mode)
            
            # Fix permissions
            os.chmod(path, requirements.required_permissions)
            
            # Verify the fix
            validation_result = self.validate_file_security(str(path), profile)
            
            return {
                'success': validation_result['valid'],
                'path': str(path),
                'old_permissions': oct(current_perms),
                'new_permissions': oct(requirements.required_permissions),
                'validation': validation_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fix permissions: {str(e)}',
                'path': str(path)
            }
    
    def _can_create_securely(self, path: Path, requirements: SecurityRequirements) -> Dict[str, Any]:
        """Check if a file can be created securely"""
        try:
            parent = path.parent
            
            # Check if parent exists and is writable
            if not parent.exists():
                # Check if we can create parent directories
                ancestor = parent
                while not ancestor.exists():
                    ancestor = ancestor.parent
                    if ancestor == ancestor.parent:  # Root reached
                        break
                
                if not os.access(ancestor, os.W_OK):
                    return {
                        'can_create': False,
                        'reason': f'Cannot write to ancestor directory: {ancestor}'
                    }
            
            if parent.exists() and not os.access(parent, os.W_OK):
                return {
                    'can_create': False,
                    'reason': f'Parent directory not writable: {parent}'
                }
            
            # Check parent directory security if required
            if requirements.parent_directory_secure and parent.exists():
                parent_issues = self._validate_parent_security(parent)
                if parent_issues:
                    return {
                        'can_create': False,
                        'reason': 'Parent directory security issues',
                        'issues': parent_issues
                    }
            
            return {
                'can_create': True,
                'parent_directory': str(parent)
            }
            
        except Exception as e:
            return {
                'can_create': False,
                'reason': f'Error checking creation capability: {str(e)}'
            }
    
    def _validate_parent_security(self, parent_path: Path) -> List[str]:
        """Validate parent directory security"""
        issues = []
        
        try:
            if not parent_path.exists():
                issues.append(f'Parent directory does not exist: {parent_path}')
                return issues
            
            parent_stat = parent_path.stat()
            parent_perms = stat.S_IMODE(parent_stat.st_mode)
            
            # Parent should not be world-writable
            if parent_perms & stat.S_IWOTH:
                issues.append(f'Parent directory is world-writable: {parent_path}')
            
            # Parent should be owned by current user or root
            if parent_stat.st_uid not in [os.getuid(), 0]:
                issues.append(f'Parent directory not owned by user or root: {parent_path}')
            
        except Exception as e:
            issues.append(f'Cannot validate parent directory security: {str(e)}')
        
        return issues
    
    def _validate_secret_file(self, path: Path) -> List[str]:
        """Additional validation for secret files"""
        issues = []
        
        try:
            # Secret files should not be in world-readable directories
            current = path.parent
            while current != current.parent:  # Until root
                if current.exists():
                    dir_perms = stat.S_IMODE(current.stat().st_mode)
                    if dir_perms & stat.S_IROTH:
                        issues.append(
                            f'Secret file in world-readable directory: {current}'
                        )
                        break
                current = current.parent
            
        except Exception as e:
            issues.append(f'Cannot validate secret file location: {str(e)}')
        
        return issues
    
    def _get_owner_info(self, stat_info: os.stat_result) -> Dict[str, Any]:
        """Get human-readable ownership information"""
        try:
            owner = pwd.getpwuid(stat_info.st_uid)
            group = grp.getgrgid(stat_info.st_gid)
            
            return {
                'user_id': stat_info.st_uid,
                'group_id': stat_info.st_gid,
                'user_name': owner.pw_name,
                'group_name': group.gr_name
            }
        except Exception:
            return {
                'user_id': stat_info.st_uid,
                'group_id': stat_info.st_gid,
                'user_name': 'unknown',
                'group_name': 'unknown'
            }
    
    def validate_directory_tree(self, root_path: str, 
                               profiles: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Validate security of an entire directory tree
        
        Args:
            root_path: Root directory to validate
            profiles: Dict mapping paths to security profiles
            
        Returns:
            Comprehensive validation result
        """
        root = Path(root_path).resolve()
        profiles = profiles or {}
        
        if not root.exists():
            return {
                'valid': False,
                'error': f'Root path does not exist: {root}',
                'path': str(root)
            }
        
        results = {
            'valid': True,
            'root_path': str(root),
            'files_validated': 0,
            'directories_validated': 0,
            'issues': [],
            'warnings': [],
            'file_results': {}
        }
        
        try:
            for file_path in root.rglob('*'):
                relative_path = str(file_path.relative_to(root))
                
                # Determine security profile
                profile = 'config_file'  # default
                for path_pattern, prof in profiles.items():
                    if path_pattern in relative_path:
                        profile = prof
                        break
                
                # Special handling for sensitive files
                if '.master_key' in file_path.name:
                    profile = 'master_key'
                elif file_path.suffix == '.db' and 'encrypted' in file_path.name:
                    profile = 'encrypted_db'
                elif file_path.is_dir() and 'data' in file_path.name:
                    profile = 'data_directory'
                
                # Validate file/directory
                validation = self.validate_file_security(str(file_path), profile)
                results['file_results'][relative_path] = validation
                
                if file_path.is_dir():
                    results['directories_validated'] += 1
                else:
                    results['files_validated'] += 1
                
                if not validation['valid']:
                    results['valid'] = False
                    results['issues'].extend([
                        f"{relative_path}: {issue}" 
                        for issue in validation.get('issues', [])
                    ])
                
                if 'warnings' in validation:
                    results['warnings'].extend([
                        f"{relative_path}: {warning}"
                        for warning in validation['warnings']
                    ])
            
        except Exception as e:
            results['valid'] = False
            results['error'] = f'Directory tree validation failed: {str(e)}'
            results['issues'].append(f'Validation error: {str(e)}')
        
        return results


# Global instance for easy import
file_security = FileSecurityValidator()


def validate_sensitive_file(file_path: str) -> Dict[str, Any]:
    """Convenience function for validating sensitive files"""
    return file_security.validate_file_security(file_path, 'master_key')


def create_secure_directory(dir_path: str) -> Dict[str, Any]:
    """Convenience function for creating secure directories"""
    return file_security.create_secure_file(dir_path, 'data_directory')


def fix_permissions(file_path: str, profile: str = 'config_file') -> Dict[str, Any]:
    """Convenience function for fixing file permissions"""
    return file_security.fix_file_permissions(file_path, profile)
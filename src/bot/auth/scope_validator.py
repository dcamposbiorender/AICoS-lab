#!/usr/bin/env python3
"""
Runtime Scope Validator for Slack Bot Operations

Validates OAuth scopes before API calls to prevent authorization errors.
Integrates with permission checker and provides detailed scope analysis.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Import from core authentication infrastructure  
try:
    from ...core.auth_manager import credential_vault
    from ...core.slack_scopes import slack_scopes, SlackScopes, ScopeCategory
    from ...core.permission_checker import (
        get_permission_checker, PermissionLevel, 
        SlackAPIRegistry, check_api_permissions
    )
except ImportError as e:
    logging.error(f"Failed to import core authentication modules: {e}")
    raise

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Scope validation levels"""
    STRICT = "strict"      # Block operations with missing scopes
    WARNING = "warning"    # Warn but allow operations  
    DISABLED = "disabled"  # No scope validation

@dataclass
class ScopeRequirement:
    """Scope requirement specification"""
    scope: str
    required: bool = True
    description: str = ""
    alternatives: List[str] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []

@dataclass
class ValidationResult:
    """Scope validation result"""
    valid: bool
    missing_scopes: List[str]
    available_scopes: List[str]
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]
    
class ScopeValidator:
    """
    Runtime scope validator for Slack bot operations
    
    Features:
    - Validates scopes before API calls
    - Provides detailed missing scope analysis
    - Suggests alternative approaches when scopes missing
    - Integrates with OAuth flow for scope upgrades
    - Caches validation results for performance
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        """
        Initialize scope validator
        
        Args:
            validation_level: How strictly to enforce scope requirements
        """
        self.validation_level = validation_level
        self.credential_vault = credential_vault
        self.slack_scopes = slack_scopes
        self.permission_checker = get_permission_checker()
        self.api_registry = SlackAPIRegistry()
        
        # Validation cache for performance
        self._validation_cache = {}
        self._scope_cache = {}
        
        logger.info(f"🔍 Scope Validator initialized with {validation_level.value} validation")
    
    def set_validation_level(self, level: ValidationLevel):
        """Update validation level and clear cache"""
        self.validation_level = level
        self._validation_cache.clear()
        logger.info(f"Scope validation level updated to: {level.value}")
    
    def validate_api_call(self, api_method: str, token_type: str = 'bot',
                         custom_scopes: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate scopes required for specific API call
        
        Args:
            api_method: Slack API method (e.g., 'chat.postMessage')
            token_type: 'bot' or 'user' token
            custom_scopes: Override default scope requirements
        
        Returns:
            ValidationResult with detailed analysis
        """
        if self.validation_level == ValidationLevel.DISABLED:
            return ValidationResult(
                valid=True,
                missing_scopes=[],
                available_scopes=[],
                warnings=[],
                errors=[],
                recommendations=[]
            )
        
        # Use permission checker for core validation
        permission_result = self.permission_checker.check_api_permissions(
            api_method, token_type, custom_scopes
        )
        
        # Convert to our ValidationResult format
        warnings = []
        errors = []
        recommendations = []
        
        if not permission_result['valid']:
            error_msg = f"Missing scopes for {api_method}: {permission_result.get('missing_scopes', [])}"
            
            if self.validation_level == ValidationLevel.WARNING:
                warnings.append(error_msg)
            else:
                errors.append(error_msg)
            
            # Add recommendations for missing scopes
            recommendations.extend(self._get_scope_recommendations(
                permission_result.get('missing_scopes', []),
                token_type
            ))
        
        return ValidationResult(
            valid=permission_result['valid'],
            missing_scopes=permission_result.get('missing_scopes', []),
            available_scopes=permission_result.get('available_scopes', []),
            warnings=warnings,
            errors=errors,
            recommendations=recommendations
        )
    
    def validate_feature_scopes(self, feature_name: str) -> ValidationResult:
        """
        Validate scopes for a complete feature
        
        Args:
            feature_name: Feature name (e.g., 'message_collection')
        
        Returns:
            ValidationResult for the feature
        """
        if self.validation_level == ValidationLevel.DISABLED:
            return ValidationResult(
                valid=True,
                missing_scopes=[],
                available_scopes=[],
                warnings=[],
                errors=[],
                recommendations=[]
            )
        
        # Get required scopes for feature
        required_scopes = self.slack_scopes.get_required_scopes_for_feature(feature_name)
        
        if not required_scopes:
            return ValidationResult(
                valid=False,
                missing_scopes=[],
                available_scopes=[],
                warnings=[],
                errors=[f"Unknown feature: {feature_name}"],
                recommendations=[]
            )
        
        # Validate bot and user scopes separately
        bot_scopes = []
        user_scopes = []
        
        for scope in required_scopes:
            scope_info = self.slack_scopes.get_scope_info(scope)
            if scope_info.get('token_type') == 'user':
                user_scopes.append(scope)
            else:
                bot_scopes.append(scope)
        
        # Validate each scope type
        all_missing = []
        all_available = []
        warnings = []
        errors = []
        
        if bot_scopes:
            bot_validation = self.credential_vault.validate_slack_permissions(bot_scopes, 'bot')
            all_missing.extend(bot_validation.get('missing_scopes', []))
            all_available.extend(bot_validation.get('available_scopes', []))
        
        if user_scopes:
            user_validation = self.credential_vault.validate_slack_permissions(user_scopes, 'user')
            all_missing.extend(user_validation.get('missing_scopes', []))
            all_available.extend(user_validation.get('available_scopes', []))
        
        # Generate messages based on validation level
        is_valid = len(all_missing) == 0
        
        if not is_valid:
            error_msg = f"Feature '{feature_name}' missing scopes: {all_missing}"
            
            if self.validation_level == ValidationLevel.WARNING:
                warnings.append(error_msg)
            else:
                errors.append(error_msg)
        
        # Generate recommendations
        recommendations = self._get_feature_recommendations(feature_name, all_missing)
        
        return ValidationResult(
            valid=is_valid,
            missing_scopes=all_missing,
            available_scopes=list(set(all_available)),
            warnings=warnings,
            errors=errors,
            recommendations=recommendations
        )
    
    def validate_command_permissions(self, command_name: str, 
                                   required_scopes: List[str],
                                   token_type: str = 'bot') -> ValidationResult:
        """
        Validate scopes for a slash command
        
        Args:
            command_name: Command name (e.g., '/cos search')
            required_scopes: Scopes required for command
            token_type: Token type needed
        
        Returns:
            ValidationResult for the command
        """
        if self.validation_level == ValidationLevel.DISABLED:
            return ValidationResult(
                valid=True,
                missing_scopes=[],
                available_scopes=[],
                warnings=[],
                errors=[],
                recommendations=[]
            )
        
        # Validate provided scopes
        validation = self.credential_vault.validate_slack_permissions(required_scopes, token_type)
        
        warnings = []
        errors = []
        recommendations = []
        
        if not validation['valid']:
            missing = validation.get('missing_scopes', [])
            error_msg = f"Command '{command_name}' missing {token_type} scopes: {missing}"
            
            if self.validation_level == ValidationLevel.WARNING:
                warnings.append(error_msg)
            else:
                errors.append(error_msg)
            
            # Add command-specific recommendations
            recommendations.extend([
                f"Command '{command_name}' requires these additional scopes:",
                *[f"  - {scope}: {self._get_scope_description(scope)}" for scope in missing],
                "Consider reinstalling the Slack app with updated scopes."
            ])
        
        return ValidationResult(
            valid=validation['valid'],
            missing_scopes=validation.get('missing_scopes', []),
            available_scopes=validation.get('available_scopes', []),
            warnings=warnings,
            errors=errors,
            recommendations=recommendations
        )
    
    def get_comprehensive_scope_analysis(self) -> Dict[str, Any]:
        """
        Get comprehensive analysis of current scope situation
        
        Returns:
            Detailed analysis of available vs required scopes
        """
        # Get current scopes
        bot_scopes = self.credential_vault.get_slack_scopes('bot') or set()
        user_scopes = self.credential_vault.get_slack_scopes('user') or set()
        
        # Get all available scope categories
        scope_analysis = {}
        
        for category in ScopeCategory:
            category_scopes = self.slack_scopes.get_scopes_by_category(category)
            
            available_in_category = len(category_scopes.intersection(bot_scopes.union(user_scopes)))
            total_in_category = len(category_scopes)
            
            scope_analysis[category.value] = {
                'available': available_in_category,
                'total': total_in_category,
                'percentage': (available_in_category / total_in_category * 100) if total_in_category > 0 else 0,
                'missing': list(category_scopes - bot_scopes.union(user_scopes))
            }
        
        # Analyze feature completeness
        feature_analysis = {}
        
        # Get common features and check completeness
        common_features = [
            'message_collection',
            'channel_management', 
            'user_directory',
            'file_management',
            'search',
            'reactions',
            'pins',
            'bookmarks'
        ]
        
        for feature in common_features:
            required_scopes = self.slack_scopes.get_required_scopes_for_feature(feature)
            if required_scopes:
                missing = required_scopes - bot_scopes.union(user_scopes)
                feature_analysis[feature] = {
                    'available': len(required_scopes - missing),
                    'total': len(required_scopes),
                    'complete': len(missing) == 0,
                    'missing': list(missing)
                }
        
        return {
            'bot_scopes': {
                'count': len(bot_scopes),
                'scopes': list(bot_scopes)
            },
            'user_scopes': {
                'count': len(user_scopes),
                'scopes': list(user_scopes)
            },
            'total_scopes': len(bot_scopes) + len(user_scopes),
            'category_analysis': scope_analysis,
            'feature_analysis': feature_analysis,
            'validation_level': self.validation_level.value,
            'recommendations': self._get_general_recommendations(bot_scopes, user_scopes)
        }
    
    def _get_scope_recommendations(self, missing_scopes: List[str], 
                                  token_type: str) -> List[str]:
        """Get recommendations for missing scopes"""
        if not missing_scopes:
            return []
        
        recommendations = [
            f"Missing {token_type} token scopes prevent this operation:",
        ]
        
        for scope in missing_scopes:
            description = self._get_scope_description(scope)
            recommendations.append(f"  - {scope}: {description}")
        
        recommendations.extend([
            "",
            "To resolve:",
            "1. Update your Slack app configuration with these scopes",
            "2. Reinstall the app to grant the new permissions",
            "3. Or use alternative API methods that don't require these scopes"
        ])
        
        return recommendations
    
    def _get_feature_recommendations(self, feature_name: str, 
                                   missing_scopes: List[str]) -> List[str]:
        """Get recommendations for missing feature scopes"""
        if not missing_scopes:
            return [f"✅ Feature '{feature_name}' has all required scopes"]
        
        return [
            f"Feature '{feature_name}' requires additional OAuth scopes:",
            *[f"  - {scope}: {self._get_scope_description(scope)}" for scope in missing_scopes],
            "",
            "Recommended actions:",
            "1. Run OAuth flow with updated scope requirements",
            "2. Update Slack app manifest with missing scopes", 
            "3. Consider feature degradation as fallback option"
        ]
    
    def _get_general_recommendations(self, bot_scopes: Set[str], 
                                   user_scopes: Set[str]) -> List[str]:
        """Get general scope recommendations"""
        recommendations = []
        
        total_possible_bot = len(self.slack_scopes.get_all_bot_scopes())
        total_possible_user = len(self.slack_scopes.get_all_user_scopes())
        
        bot_coverage = len(bot_scopes) / total_possible_bot * 100
        user_coverage = len(user_scopes) / total_possible_user * 100
        
        if bot_coverage < 50:
            recommendations.append(f"Bot scope coverage is low ({bot_coverage:.1f}%) - consider requesting more comprehensive scopes")
        
        if user_coverage < 20:
            recommendations.append(f"User scope coverage is minimal ({user_coverage:.1f}%) - some features may be limited")
        
        # Check for essential missing scopes
        essential_bot = {'chat:write', 'channels:read', 'users:read'}
        essential_user = {'identity.basic'}
        
        missing_essential_bot = essential_bot - bot_scopes
        missing_essential_user = essential_user - user_scopes
        
        if missing_essential_bot:
            recommendations.append(f"Missing essential bot scopes: {list(missing_essential_bot)}")
        
        if missing_essential_user:
            recommendations.append(f"Missing essential user scopes: {list(missing_essential_user)}")
        
        if not recommendations:
            recommendations.append("✅ Scope configuration looks comprehensive")
        
        return recommendations
    
    def _get_scope_description(self, scope: str) -> str:
        """Get human-readable description for a scope"""
        scope_info = self.slack_scopes.get_scope_info(scope)
        return scope_info.get('description', 'No description available')
    
    def clear_cache(self):
        """Clear validation cache"""
        self._validation_cache.clear()
        self._scope_cache.clear()
        logger.info("Scope validation cache cleared")

# Decorator for automatic scope validation
def validate_scopes(required_scopes: List[str], token_type: str = 'bot',
                   validation_level: Optional[ValidationLevel] = None):
    """
    Decorator to validate scopes before function execution
    
    Args:
        required_scopes: List of required OAuth scopes
        token_type: 'bot' or 'user' token type
        validation_level: Override default validation level
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = ScopeValidator(validation_level or ValidationLevel.STRICT)
            
            # Create a synthetic API method name from function
            api_method = getattr(func, '__name__', 'unknown_method')
            
            # Validate using custom scopes
            result = validator.validate_api_call(api_method, token_type, required_scopes)
            
            if not result.valid and validator.validation_level == ValidationLevel.STRICT:
                error_msg = f"Scope validation failed for {func.__name__}: {result.errors}"
                logger.error(error_msg)
                raise PermissionError(error_msg)
            
            elif result.warnings:
                for warning in result.warnings:
                    logger.warning(warning)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global validator instance
_global_validator = None

def get_scope_validator() -> ScopeValidator:
    """Get global scope validator instance"""
    global _global_validator
    if _global_validator is None:
        _global_validator = ScopeValidator()
    return _global_validator

# Convenience functions
def validate_api_scopes(api_method: str, token_type: str = 'bot') -> ValidationResult:
    """Validate scopes for API method using global validator"""
    return get_scope_validator().validate_api_call(api_method, token_type)

def validate_feature_scopes(feature_name: str) -> ValidationResult:
    """Validate scopes for feature using global validator"""
    return get_scope_validator().validate_feature_scopes(feature_name)
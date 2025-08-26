#!/usr/bin/env python3
"""
Slack OAuth Scopes Configuration
Comprehensive definition of all Slack OAuth scopes with descriptions and categorization
"""

from typing import Dict, List, Set
from enum import Enum

class ScopeCategory(Enum):
    """Categories for organizing OAuth scopes"""
    CHANNELS = "channels"
    MESSAGING = "messaging"
    USER_DATA = "user_data"
    FILES = "files"
    CALLS = "calls"
    ADMIN = "admin"
    BOOKMARKS = "bookmarks"
    EMOJI = "emoji"
    SEARCH = "search"
    TEAM = "team"
    WORKFLOW = "workflow"
    DND = "dnd"
    REMINDERS = "reminders"
    STARS = "stars"
    PINS = "pins"
    REACTIONS = "reactions"
    USERGROUPS = "usergroups"
    IM = "im"

class SlackScopes:
    """Comprehensive Slack OAuth scopes configuration"""
    
    # Bot Token Scopes (xoxb- prefix)
    BOT_SCOPES = {
        # Bookmarks
        'bookmarks:read': {
            'description': 'View bookmarks in channels and conversations',
            'category': ScopeCategory.BOOKMARKS,
            'required_for': ['bookmark_listing', 'channel_context']
        },
        'bookmarks:write': {
            'description': 'Add and edit bookmarks in channels and conversations',
            'category': ScopeCategory.BOOKMARKS,
            'required_for': ['bookmark_management', 'channel_organization']
        },
        
        # Calls
        'calls:read': {
            'description': 'View information about ongoing and past calls',
            'category': ScopeCategory.CALLS,
            'required_for': ['call_monitoring', 'meeting_context']
        },
        'calls:write': {
            'description': 'Start and manage calls in channels and conversations',
            'category': ScopeCategory.CALLS,
            'required_for': ['call_initiation', 'meeting_scheduling']
        },
        
        # Channels
        'channels:history': {
            'description': 'View messages and content in public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['message_collection', 'conversation_analysis']
        },
        'channels:read': {
            'description': 'View basic information about public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['channel_discovery', 'workspace_mapping']
        },
        'channels:write': {
            'description': 'Manage public channels (create, archive, rename)',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['channel_management', 'workspace_organization']
        },
        'channels:write.invites': {
            'description': 'Invite members to public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['member_management', 'channel_growth']
        },
        'channels:write.topic': {
            'description': 'Edit topics and purposes in public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['channel_organization', 'topic_management']
        },
        
        # Chat/Messaging
        'chat:write': {
            'description': 'Send messages as the bot',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['bot_communication', 'automated_responses']
        },
        'chat:write.customize': {
            'description': 'Send messages with custom name and avatar',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['branded_messaging', 'persona_management']
        },
        'chat:write.public': {
            'description': 'Send messages to public channels without joining',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['broadcast_messaging', 'announcements']
        },
        
        # Commands
        'commands': {
            'description': 'Add slash commands that people can use',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['slash_commands', 'bot_interface']
        },
        
        # Do Not Disturb
        'dnd:read': {
            'description': 'View Do Not Disturb settings for people',
            'category': ScopeCategory.DND,
            'required_for': ['availability_checking', 'smart_scheduling']
        },
        
        # Emoji
        'emoji:read': {
            'description': 'View custom emoji in the workspace',
            'category': ScopeCategory.EMOJI,
            'required_for': ['emoji_analysis', 'reaction_context']
        },
        
        # Files
        'files:read': {
            'description': 'View files shared in channels and conversations',
            'category': ScopeCategory.FILES,
            'required_for': ['file_collection', 'content_analysis']
        },
        'files:write': {
            'description': 'Upload, edit, and delete files',
            'category': ScopeCategory.FILES,
            'required_for': ['file_management', 'content_sharing']
        },
        
        # Groups (Private Channels)
        'groups:history': {
            'description': 'View messages and content in private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_analysis', 'comprehensive_collection']
        },
        'groups:read': {
            'description': 'View basic information about private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_discovery', 'workspace_mapping']
        },
        'groups:write': {
            'description': 'Manage private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_management']
        },
        'groups:write.invites': {
            'description': 'Invite members to private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_member_management']
        },
        'groups:write.topic': {
            'description': 'Edit topics and purposes in private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_organization']
        },
        
        # Direct Messages
        'im:history': {
            'description': 'View messages in direct messages with the bot',
            'category': ScopeCategory.IM,
            'required_for': ['dm_collection', 'private_conversations']
        },
        'im:read': {
            'description': 'View basic information about direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['dm_discovery', 'conversation_mapping']
        },
        'im:write': {
            'description': 'Start direct messages with people',
            'category': ScopeCategory.IM,
            'required_for': ['dm_initiation', 'private_messaging']
        },
        
        # Incoming Webhooks
        'incoming-webhook': {
            'description': 'Post messages to channels with incoming webhooks',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['webhook_posting', 'external_integrations']
        },
        
        # Metadata
        'metadata.message:read': {
            'description': 'View message metadata in channels and conversations',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['message_analysis', 'metadata_collection']
        },
        
        # Multi-party Direct Messages
        'mpim:history': {
            'description': 'View messages and content in group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['group_dm_collection', 'multi_party_conversations']
        },
        'mpim:read': {
            'description': 'View basic information about group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['group_dm_discovery']
        },
        'mpim:write': {
            'description': 'Start and manage group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['group_dm_management']
        },
        
        # Pins
        'pins:read': {
            'description': 'View pinned messages and files',
            'category': ScopeCategory.PINS,
            'required_for': ['pinned_content_analysis', 'important_message_tracking']
        },
        'pins:write': {
            'description': 'Pin and unpin messages and files',
            'category': ScopeCategory.PINS,
            'required_for': ['content_curation', 'message_highlighting']
        },
        
        # Reactions
        'reactions:read': {
            'description': 'View emoji reactions to messages and files',
            'category': ScopeCategory.REACTIONS,
            'required_for': ['sentiment_analysis', 'engagement_metrics']
        },
        'reactions:write': {
            'description': 'Add and remove emoji reactions',
            'category': ScopeCategory.REACTIONS,
            'required_for': ['bot_reactions', 'engagement_responses']
        },
        
        # Reminders
        'reminders:read': {
            'description': 'View reminders created by team members',
            'category': ScopeCategory.REMINDERS,
            'required_for': ['reminder_tracking', 'task_monitoring']
        },
        'reminders:write': {
            'description': 'Add, edit, and delete reminders',
            'category': ScopeCategory.REMINDERS,
            'required_for': ['reminder_management', 'task_automation']
        },
        
        # Search
        'search:read': {
            'description': 'Search messages, files, and channels',
            'category': ScopeCategory.SEARCH,
            'required_for': ['content_search', 'information_retrieval']
        },
        
        # Stars
        'stars:read': {
            'description': 'View starred messages and files',
            'category': ScopeCategory.STARS,
            'required_for': ['starred_content_tracking', 'user_preferences']
        },
        'stars:write': {
            'description': 'Add and remove stars from messages and files',
            'category': ScopeCategory.STARS,
            'required_for': ['content_starring', 'preference_management']
        },
        
        # Team
        'team:read': {
            'description': 'View the workspace name, email domain, and icon',
            'category': ScopeCategory.TEAM,
            'required_for': ['workspace_info', 'team_context']
        },
        
        # User Groups
        'usergroups:read': {
            'description': 'View User Groups in the workspace',
            'category': ScopeCategory.USERGROUPS,
            'required_for': ['group_analysis', 'organization_mapping']
        },
        'usergroups:write': {
            'description': 'Create and manage User Groups',
            'category': ScopeCategory.USERGROUPS,
            'required_for': ['group_management', 'team_organization']
        },
        
        # Users
        'users:read': {
            'description': 'View people in the workspace',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['user_directory', 'team_mapping']
        },
        'users:read.email': {
            'description': 'View email addresses of people in the workspace',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['email_mapping', 'contact_integration']
        },
        
        # Workflow
        'workflow.steps:execute': {
            'description': 'Add steps to workflows and workflows can run',
            'category': ScopeCategory.WORKFLOW,
            'required_for': ['workflow_automation', 'process_integration']
        }
    }
    
    # User Token Scopes (xoxp- prefix)
    USER_SCOPES = {
        # Admin
        'admin': {
            'description': 'Administer the workspace',
            'category': ScopeCategory.ADMIN,
            'required_for': ['workspace_administration', 'admin_actions']
        },
        
        # Channels
        'channels:history': {
            'description': 'View messages and content in public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['comprehensive_message_collection', 'full_channel_access']
        },
        'channels:read': {
            'description': 'View basic information about public channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['channel_discovery', 'workspace_mapping']
        },
        'channels:write': {
            'description': 'Manage public channels on behalf of the user',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['user_channel_management']
        },
        
        # Chat
        'chat:write': {
            'description': 'Send messages on behalf of the user',
            'category': ScopeCategory.MESSAGING,
            'required_for': ['user_messaging', 'impersonation']
        },
        
        # Do Not Disturb
        'dnd:read': {
            'description': 'View Do Not Disturb settings',
            'category': ScopeCategory.DND,
            'required_for': ['availability_checking']
        },
        'dnd:write': {
            'description': 'Edit Do Not Disturb settings',
            'category': ScopeCategory.DND,
            'required_for': ['availability_management']
        },
        
        # Emoji
        'emoji:read': {
            'description': 'View custom emoji',
            'category': ScopeCategory.EMOJI,
            'required_for': ['emoji_analysis']
        },
        
        # Files
        'files:read': {
            'description': 'View files shared in channels and conversations',
            'category': ScopeCategory.FILES,
            'required_for': ['comprehensive_file_access']
        },
        'files:write': {
            'description': 'Upload, edit, and delete files on behalf of the user',
            'category': ScopeCategory.FILES,
            'required_for': ['user_file_management']
        },
        
        # Groups (Private Channels)
        'groups:history': {
            'description': 'View messages and content in private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_collection']
        },
        'groups:read': {
            'description': 'View basic information about private channels',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['private_channel_discovery']
        },
        'groups:write': {
            'description': 'Manage private channels on behalf of the user',
            'category': ScopeCategory.CHANNELS,
            'required_for': ['user_private_channel_management']
        },
        
        # Identity
        'identity.basic': {
            'description': 'View basic information about the user',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['user_identification', 'profile_access']
        },
        'identity.email': {
            'description': 'View the user\'s email address',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['email_verification', 'contact_info']
        },
        'identity.team': {
            'description': 'View the user\'s workspace information',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['workspace_context']
        },
        
        # Direct Messages
        'im:history': {
            'description': 'View messages in direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['dm_collection', 'private_message_access']
        },
        'im:read': {
            'description': 'View basic information about direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['dm_discovery']
        },
        'im:write': {
            'description': 'Start direct messages on behalf of the user',
            'category': ScopeCategory.IM,
            'required_for': ['user_dm_management']
        },
        
        # Multi-party Direct Messages
        'mpim:history': {
            'description': 'View messages in group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['group_dm_collection']
        },
        'mpim:read': {
            'description': 'View basic information about group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['group_dm_discovery']
        },
        'mpim:write': {
            'description': 'Start and manage group direct messages',
            'category': ScopeCategory.IM,
            'required_for': ['user_group_dm_management']
        },
        
        # Pins
        'pins:read': {
            'description': 'View pinned content',
            'category': ScopeCategory.PINS,
            'required_for': ['pinned_content_access']
        },
        'pins:write': {
            'description': 'Pin and unpin content on behalf of the user',
            'category': ScopeCategory.PINS,
            'required_for': ['user_pin_management']
        },
        
        # Reactions
        'reactions:read': {
            'description': 'View emoji reactions',
            'category': ScopeCategory.REACTIONS,
            'required_for': ['reaction_analysis']
        },
        'reactions:write': {
            'description': 'Add and remove emoji reactions',
            'category': ScopeCategory.REACTIONS,
            'required_for': ['user_reactions']
        },
        
        # Reminders
        'reminders:read': {
            'description': 'View reminders',
            'category': ScopeCategory.REMINDERS,
            'required_for': ['reminder_access']
        },
        'reminders:write': {
            'description': 'Add, edit, and delete reminders',
            'category': ScopeCategory.REMINDERS,
            'required_for': ['user_reminder_management']
        },
        
        # Search
        'search:read': {
            'description': 'Search messages, files, and channels',
            'category': ScopeCategory.SEARCH,
            'required_for': ['comprehensive_search']
        },
        
        # Stars
        'stars:read': {
            'description': 'View starred content',
            'category': ScopeCategory.STARS,
            'required_for': ['starred_content_access']
        },
        'stars:write': {
            'description': 'Add and remove stars',
            'category': ScopeCategory.STARS,
            'required_for': ['user_starring']
        },
        
        # Team
        'team:read': {
            'description': 'View workspace information',
            'category': ScopeCategory.TEAM,
            'required_for': ['workspace_details']
        },
        
        # User Groups
        'usergroups:read': {
            'description': 'View User Groups',
            'category': ScopeCategory.USERGROUPS,
            'required_for': ['group_information']
        },
        'usergroups:write': {
            'description': 'Create and manage User Groups',
            'category': ScopeCategory.USERGROUPS,
            'required_for': ['user_group_management']
        },
        
        # Users
        'users:read': {
            'description': 'View people in the workspace',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['user_directory_access']
        },
        'users:read.email': {
            'description': 'View email addresses',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['email_access']
        },
        'users:write': {
            'description': 'Set presence and profile information',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['profile_management']
        },
        
        # Users Profile
        'users.profile:read': {
            'description': 'View profile information for people',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['profile_access']
        },
        'users.profile:write': {
            'description': 'Edit profile information',
            'category': ScopeCategory.USER_DATA,
            'required_for': ['profile_editing']
        }
    }
    
    @classmethod
    def get_all_bot_scopes(cls) -> Set[str]:
        """Get all bot token scope names"""
        return set(cls.BOT_SCOPES.keys())
    
    @classmethod
    def get_all_user_scopes(cls) -> Set[str]:
        """Get all user token scope names"""
        return set(cls.USER_SCOPES.keys())
    
    @classmethod
    def get_all_scopes(cls) -> Set[str]:
        """Get all scope names (bot + user)"""
        return cls.get_all_bot_scopes().union(cls.get_all_user_scopes())
    
    @classmethod
    def get_scopes_by_category(cls, category: ScopeCategory, token_type: str = 'both') -> Set[str]:
        """Get scopes filtered by category and token type"""
        scopes = set()
        
        if token_type in ['bot', 'both']:
            scopes.update([
                scope for scope, info in cls.BOT_SCOPES.items()
                if info['category'] == category
            ])
        
        if token_type in ['user', 'both']:
            scopes.update([
                scope for scope, info in cls.USER_SCOPES.items()
                if info['category'] == category
            ])
        
        return scopes
    
    @classmethod
    def get_scope_info(cls, scope_name: str) -> Dict:
        """Get detailed information about a specific scope"""
        if scope_name in cls.BOT_SCOPES:
            info = cls.BOT_SCOPES[scope_name].copy()
            info['token_type'] = 'bot'
            return info
        elif scope_name in cls.USER_SCOPES:
            info = cls.USER_SCOPES[scope_name].copy()
            info['token_type'] = 'user'
            return info
        else:
            return {}
    
    @classmethod
    def validate_scopes(cls, scopes: List[str], token_type: str = 'bot') -> Dict:
        """Validate a list of scopes against available scopes"""
        available = cls.BOT_SCOPES if token_type == 'bot' else cls.USER_SCOPES
        
        valid_scopes = []
        invalid_scopes = []
        
        for scope in scopes:
            if scope in available:
                valid_scopes.append(scope)
            else:
                invalid_scopes.append(scope)
        
        return {
            'valid': valid_scopes,
            'invalid': invalid_scopes,
            'all_valid': len(invalid_scopes) == 0
        }
    
    @classmethod
    def get_required_scopes_for_feature(cls, feature: str) -> Set[str]:
        """Get all scopes required for a specific feature"""
        required_scopes = set()
        
        # Search through all scopes for the feature
        for scope, info in {**cls.BOT_SCOPES, **cls.USER_SCOPES}.items():
            if feature in info.get('required_for', []):
                required_scopes.add(scope)
        
        return required_scopes
    
    @classmethod
    def get_minimal_scope_set(cls) -> Dict[str, List[str]]:
        """Get minimal scope sets for common use cases"""
        return {
            'basic_messaging': [
                'chat:write',
                'channels:read',
                'users:read'
            ],
            'comprehensive_collection': [
                'channels:history',
                'channels:read',
                'groups:history',
                'groups:read',
                'im:history',
                'im:read',
                'mpim:history',
                'mpim:read',
                'files:read',
                'users:read',
                'users:read.email'
            ],
            'content_management': [
                'files:write',
                'pins:write',
                'reactions:write',
                'stars:write',
                'bookmarks:write'
            ],
            'admin_functions': [
                'channels:write',
                'groups:write',
                'usergroups:write',
                'reminders:write'
            ]
        }

# Global scope registry for easy access
slack_scopes = SlackScopes()
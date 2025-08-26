#!/usr/bin/env python3
"""
Slack OAuth Scopes Management Tool
Provides CLI interface for managing, validating, and analyzing Slack OAuth scopes
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Set, Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.auth_manager import credential_vault
from core.slack_scopes import slack_scopes, ScopeCategory

class SlackScopeManager:
    """Management interface for Slack OAuth scopes"""
    
    def __init__(self):
        self.credential_vault = credential_vault
        self.slack_scopes = slack_scopes
        
    def list_all_scopes(self, token_type: str = 'both', category: str = None) -> Dict[str, Any]:
        """List all available OAuth scopes"""
        result = {
            'bot_scopes': {},
            'user_scopes': {},
            'total_count': 0
        }
        
        # Filter by category if specified
        category_filter = None
        if category:
            try:
                category_filter = ScopeCategory(category.lower())
            except ValueError:
                print(f"❌ Invalid category: {category}")
                print(f"Available categories: {[c.value for c in ScopeCategory]}")
                return result
        
        if token_type in ['bot', 'both']:
            if category_filter:
                bot_scopes = self.slack_scopes.get_scopes_by_category(category_filter, 'bot')
                result['bot_scopes'] = {
                    scope: self.slack_scopes.get_scope_info(scope) 
                    for scope in bot_scopes
                }
            else:
                result['bot_scopes'] = self.slack_scopes.BOT_SCOPES
        
        if token_type in ['user', 'both']:
            if category_filter:
                user_scopes = self.slack_scopes.get_scopes_by_category(category_filter, 'user')
                result['user_scopes'] = {
                    scope: self.slack_scopes.get_scope_info(scope) 
                    for scope in user_scopes
                }
            else:
                result['user_scopes'] = self.slack_scopes.USER_SCOPES
        
        result['total_count'] = len(result['bot_scopes']) + len(result['user_scopes'])
        return result
    
    def show_current_scopes(self, token_type: str = 'both') -> Dict[str, Any]:
        """Show currently stored OAuth scopes"""
        result = {
            'bot_scopes': None,
            'user_scopes': None,
            'bot_count': 0,
            'user_count': 0
        }
        
        if token_type in ['bot', 'both']:
            bot_scopes = self.credential_vault.get_slack_scopes('bot')
            if bot_scopes:
                result['bot_scopes'] = sorted(list(bot_scopes))
                result['bot_count'] = len(bot_scopes)
        
        if token_type in ['user', 'both']:
            user_scopes = self.credential_vault.get_slack_scopes('user')
            if user_scopes:
                result['user_scopes'] = sorted(list(user_scopes))
                result['user_count'] = len(user_scopes)
        
        return result
    
    def store_scopes_from_list(self, scopes: List[str], token_type: str = 'bot') -> bool:
        """Store OAuth scopes from a provided list"""
        if not scopes:
            print("❌ No scopes provided")
            return False
        
        print(f"📝 Storing {len(scopes)} {token_type} scopes...")
        
        # Validate scopes
        validation = self.slack_scopes.validate_scopes(scopes, token_type)
        if not validation['all_valid']:
            print(f"⚠️ Invalid scopes detected: {validation['invalid']}")
            print("Valid scopes will be stored, invalid ones ignored")
            scopes = validation['valid']
        
        # Store the scopes
        success = self.credential_vault.store_slack_scopes(scopes, token_type)
        
        if success:
            print(f"✅ Successfully stored {len(scopes)} {token_type} scopes")
            return True
        else:
            print(f"❌ Failed to store {token_type} scopes")
            return False
    
    def validate_feature_permissions(self, feature: str, token_type: str = 'bot') -> Dict[str, Any]:
        """Validate permissions for a specific feature"""
        required_scopes = list(self.slack_scopes.get_required_scopes_for_feature(feature))
        
        if not required_scopes:
            print(f"⚠️ No scope requirements found for feature: {feature}")
            return {'valid': False, 'error': 'Feature not found'}
        
        validation = self.credential_vault.validate_slack_permissions(required_scopes, token_type)
        return validation
    
    def analyze_scope_coverage(self) -> Dict[str, Any]:
        """Analyze OAuth scope coverage across categories"""
        current_bot_scopes = self.credential_vault.get_slack_scopes('bot') or set()
        current_user_scopes = self.credential_vault.get_slack_scopes('user') or set()
        
        # Analyze by category
        coverage_by_category = {}
        for category in ScopeCategory:
            total_bot = len(self.slack_scopes.get_scopes_by_category(category, 'bot'))
            total_user = len(self.slack_scopes.get_scopes_by_category(category, 'user'))
            
            current_bot_in_category = len(
                self.slack_scopes.get_scopes_by_category(category, 'bot') & current_bot_scopes
            )
            current_user_in_category = len(
                self.slack_scopes.get_scopes_by_category(category, 'user') & current_user_scopes
            )
            
            coverage_by_category[category.value] = {
                'bot': {
                    'available': total_bot,
                    'current': current_bot_in_category,
                    'percentage': (current_bot_in_category / total_bot * 100) if total_bot > 0 else 0
                },
                'user': {
                    'available': total_user,
                    'current': current_user_in_category,
                    'percentage': (current_user_in_category / total_user * 100) if total_user > 0 else 0
                }
            }
        
        # Overall coverage
        total_bot_scopes = len(self.slack_scopes.get_all_bot_scopes())
        total_user_scopes = len(self.slack_scopes.get_all_user_scopes())
        
        return {
            'overall': {
                'bot': {
                    'available': total_bot_scopes,
                    'current': len(current_bot_scopes),
                    'percentage': (len(current_bot_scopes) / total_bot_scopes * 100) if total_bot_scopes > 0 else 0
                },
                'user': {
                    'available': total_user_scopes,
                    'current': len(current_user_scopes),
                    'percentage': (len(current_user_scopes) / total_user_scopes * 100) if total_user_scopes > 0 else 0
                }
            },
            'by_category': coverage_by_category
        }
    
    def export_scopes(self, output_file: str, format_type: str = 'json') -> bool:
        """Export current scopes to file"""
        current_scopes = self.show_current_scopes()
        
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'bot_scopes': current_scopes['bot_scopes'],
                'user_scopes': current_scopes['user_scopes'],
                'counts': {
                    'bot_scopes': current_scopes['bot_count'],
                    'user_scopes': current_scopes['user_count'],
                    'total': current_scopes['bot_count'] + current_scopes['user_count']
                }
            }
            
            if format_type == 'json':
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            elif format_type == 'txt':
                with open(output_path, 'w') as f:
                    f.write("Slack OAuth Scopes Export\n")
                    f.write("=" * 40 + "\n")
                    f.write(f"Exported: {export_data['exported_at']}\n\n")
                    
                    if export_data['bot_scopes']:
                        f.write("Bot Scopes:\n")
                        for scope in export_data['bot_scopes']:
                            f.write(f"  - {scope}\n")
                        f.write("\n")
                    
                    if export_data['user_scopes']:
                        f.write("User Scopes:\n")
                        for scope in export_data['user_scopes']:
                            f.write(f"  - {scope}\n")
                        f.write("\n")
                    
                    f.write(f"Total: {export_data['counts']['total']} scopes\n")
            
            print(f"✅ Scopes exported to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export scopes: {e}")
            return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Manage Slack OAuth scopes")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List scopes command
    list_parser = subparsers.add_parser('list', help='List available OAuth scopes')
    list_parser.add_argument('--type', choices=['bot', 'user', 'both'], default='both',
                           help='Token type to list scopes for')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--detail', action='store_true', help='Show detailed scope information')
    
    # Show current command
    current_parser = subparsers.add_parser('current', help='Show currently stored scopes')
    current_parser.add_argument('--type', choices=['bot', 'user', 'both'], default='both',
                              help='Token type to show scopes for')
    
    # Store scopes command
    store_parser = subparsers.add_parser('store', help='Store OAuth scopes')
    store_parser.add_argument('--type', choices=['bot', 'user'], default='bot',
                            help='Token type for scopes')
    store_parser.add_argument('--file', help='JSON file containing scopes list')
    store_parser.add_argument('--scopes', nargs='+', help='Space-separated list of scopes')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate permissions for a feature')
    validate_parser.add_argument('feature', help='Feature name to validate')
    validate_parser.add_argument('--type', choices=['bot', 'user'], default='bot',
                               help='Token type to validate')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze scope coverage')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export current scopes')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument('--format', choices=['json', 'txt'], default='json',
                             help='Export format')
    
    # Install command (store the 80+ scopes from the system)
    install_parser = subparsers.add_parser('install', help='Install comprehensive OAuth scopes')
    install_parser.add_argument('--type', choices=['bot', 'user', 'both'], default='both',
                              help='Token type to install scopes for')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = SlackScopeManager()
    
    try:
        if args.command == 'list':
            result = manager.list_all_scopes(args.type, args.category)
            
            print(f"\n📋 Available OAuth Scopes ({result['total_count']} total)")
            print("=" * 50)
            
            if args.type in ['bot', 'both'] and result['bot_scopes']:
                print(f"\n🤖 Bot Scopes ({len(result['bot_scopes'])} total):")
                for scope, info in result['bot_scopes'].items():
                    if args.detail:
                        print(f"  • {scope}")
                        print(f"    Description: {info['description']}")
                        print(f"    Category: {info['category'].value}")
                        if info.get('required_for'):
                            print(f"    Required for: {', '.join(info['required_for'])}")
                        print()
                    else:
                        print(f"  • {scope} - {info['description']}")
            
            if args.type in ['user', 'both'] and result['user_scopes']:
                print(f"\n👤 User Scopes ({len(result['user_scopes'])} total):")
                for scope, info in result['user_scopes'].items():
                    if args.detail:
                        print(f"  • {scope}")
                        print(f"    Description: {info['description']}")
                        print(f"    Category: {info['category'].value}")
                        if info.get('required_for'):
                            print(f"    Required for: {', '.join(info['required_for'])}")
                        print()
                    else:
                        print(f"  • {scope} - {info['description']}")
        
        elif args.command == 'current':
            result = manager.show_current_scopes(args.type)
            
            print(f"\n🔐 Currently Stored OAuth Scopes")
            print("=" * 40)
            
            if args.type in ['bot', 'both']:
                if result['bot_scopes']:
                    print(f"\n🤖 Bot Scopes ({result['bot_count']} total):")
                    for scope in result['bot_scopes']:
                        print(f"  • {scope}")
                else:
                    print(f"\n🤖 Bot Scopes: None stored")
            
            if args.type in ['user', 'both']:
                if result['user_scopes']:
                    print(f"\n👤 User Scopes ({result['user_count']} total):")
                    for scope in result['user_scopes']:
                        print(f"  • {scope}")
                else:
                    print(f"\n👤 User Scopes: None stored")
        
        elif args.command == 'store':
            scopes_to_store = []
            
            if args.file:
                try:
                    with open(args.file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            scopes_to_store = data
                        elif isinstance(data, dict) and f'{args.type}_scopes' in data:
                            scopes_to_store = data[f'{args.type}_scopes']
                        else:
                            print("❌ Invalid JSON format. Expected list of scopes or dict with '{type}_scopes' key")
                            return
                except Exception as e:
                    print(f"❌ Failed to read file {args.file}: {e}")
                    return
            
            elif args.scopes:
                scopes_to_store = args.scopes
            
            else:
                print("❌ Must provide either --file or --scopes")
                return
            
            success = manager.store_scopes_from_list(scopes_to_store, args.type)
            if not success:
                sys.exit(1)
        
        elif args.command == 'validate':
            result = manager.validate_feature_permissions(args.feature, args.type)
            
            print(f"\n🔍 Permission Validation for '{args.feature}'")
            print("=" * 50)
            
            if 'error' in result:
                print(f"❌ {result['error']}")
                return
            
            status = "✅" if result['valid'] else "❌"
            print(f"{status} Validation Result: {'PASS' if result['valid'] else 'FAIL'}")
            
            print(f"\n📋 Required Scopes ({len(result['required_scopes'])} total):")
            for scope in result['required_scopes']:
                has_scope = scope in result.get('available_scopes', [])
                status = "✅" if has_scope else "❌"
                print(f"  {status} {scope}")
            
            if result['missing_scopes']:
                print(f"\n⚠️ Missing Scopes ({len(result['missing_scopes'])} total):")
                for scope in result['missing_scopes']:
                    print(f"  • {scope}")
        
        elif args.command == 'analyze':
            result = manager.analyze_scope_coverage()
            
            print(f"\n📊 OAuth Scope Coverage Analysis")
            print("=" * 40)
            
            # Overall coverage
            overall = result['overall']
            print(f"\n🎯 Overall Coverage:")
            print(f"  🤖 Bot: {overall['bot']['current']}/{overall['bot']['available']} ({overall['bot']['percentage']:.1f}%)")
            print(f"  👤 User: {overall['user']['current']}/{overall['user']['available']} ({overall['user']['percentage']:.1f}%)")
            
            # Category breakdown
            print(f"\n📂 Coverage by Category:")
            for category, data in result['by_category'].items():
                if data['bot']['available'] > 0 or data['user']['available'] > 0:
                    print(f"\n  {category.title()}:")
                    if data['bot']['available'] > 0:
                        print(f"    🤖 Bot: {data['bot']['current']}/{data['bot']['available']} ({data['bot']['percentage']:.1f}%)")
                    if data['user']['available'] > 0:
                        print(f"    👤 User: {data['user']['current']}/{data['user']['available']} ({data['user']['percentage']:.1f}%)")
        
        elif args.command == 'export':
            success = manager.export_scopes(args.output, args.format)
            if not success:
                sys.exit(1)
        
        elif args.command == 'install':
            print(f"🔧 Installing comprehensive OAuth scopes...")
            
            success = True
            
            if args.type in ['bot', 'both']:
                bot_scopes = list(manager.slack_scopes.get_all_bot_scopes())
                print(f"📦 Installing {len(bot_scopes)} bot scopes...")
                success &= manager.store_scopes_from_list(bot_scopes, 'bot')
            
            if args.type in ['user', 'both']:
                user_scopes = list(manager.slack_scopes.get_all_user_scopes())
                print(f"📦 Installing {len(user_scopes)} user scopes...")
                success &= manager.store_scopes_from_list(user_scopes, 'user')
            
            if success:
                print("✅ Comprehensive OAuth scopes installed successfully")
            else:
                print("❌ Some scope installations failed")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
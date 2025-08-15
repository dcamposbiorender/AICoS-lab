"""
Comprehensive mock Google Drive data for testing collector wrappers.
Covers file changes, permission modifications, folder structures - METADATA ONLY.
Data is deterministic - same function calls return identical results.
Privacy-first: No file content stored, only metadata and audit trails.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from enum import Enum

# Base timestamp for deterministic data
BASE_DT = datetime(2025, 8, 15, 9, 0, 0)

class DriveItemType(Enum):
    FILE = "file"
    FOLDER = "folder"
    SHORTCUT = "shortcut"

class ChangeType(Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    PERMISSION_CHANGE = "permission_change"
    SHARE = "share"
    UNSHARE = "unshare"

def get_mock_drive_files() -> List[Dict[str, Any]]:
    """
    Mock Google Drive files and folders with metadata only.
    NO FILE CONTENT - only metadata for audit trail and change tracking.
    Covers various file types, sharing states, and organizational structures.
    """
    
    def dt_to_str(dt):
        return dt.isoformat() + "Z"
    
    return [
        # Root company folder (shared with organization)
        {
            "kind": "drive#file",
            "id": "folder_root_company",
            "name": "Company Documents",
            "mimeType": "application/vnd.google-apps.folder",
            "description": "Root folder for all company documents",
            "parents": [],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=365)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(hours=2)),
            "lastModifyingUser": {
                "displayName": "Alice Johnson",
                "emailAddress": "alice@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/default-user=s64"
            },
            "owners": [
                {
                    "displayName": "Alice Johnson", 
                    "emailAddress": "alice@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "alice_permission_id"
                }
            ],
            "size": "0",  # Folders have no size
            "quotaBytesUsed": "0",
            "version": "15",
            "webViewLink": "https://drive.google.com/drive/folders/folder_root_company",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.google-apps.folder",
            "hasThumbnail": False,
            "thumbnailVersion": "0",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(hours=1)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": True,
            "capabilities": {
                "canAddChildren": True,
                "canChangeCopyRequiresWriterPermission": True,
                "canChangeViewersCanCopyContent": True,
                "canComment": True,
                "canCopy": True,
                "canDelete": True,
                "canDownload": True,
                "canEdit": True,
                "canListChildren": True,
                "canModifyContent": True,
                "canMoveChildrenWithinDrive": True,
                "canMoveItemIntoTeamDrive": False,
                "canMoveItemOutOfDrive": False,
                "canReadRevisions": False,
                "canRemoveChildren": True,
                "canRename": True,
                "canShare": True,
                "canTrash": False,
                "canUntrash": False
            },
            "copyRequiresWriterPermission": False,
            "writersCanShare": True,
            "viewersCanCopyContent": True,
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_org_wide",
                    "type": "domain",
                    "domain": "company.com",
                    "role": "writer",
                    "displayName": "company.com"
                }
            ],
            "permissionIds": ["permission_org_wide"],
            "isAppAuthorized": True,
            "exportLinks": {},
            "shortcutDetails": None,
            "contentRestrictions": [],
            "resourceKey": None,
            "linkShareMetadata": {
                "securityUpdateEligible": True,
                "securityUpdateEnabled": True
            }
        },
        
        # Engineering folder
        {
            "kind": "drive#file",
            "id": "folder_engineering",
            "name": "Engineering",
            "mimeType": "application/vnd.google-apps.folder",
            "description": "Engineering team documents and specifications",
            "parents": ["folder_root_company"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=300)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(hours=6)),
            "lastModifyingUser": {
                "displayName": "Bob Smith",
                "emailAddress": "bob@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/bob-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Alice Johnson",
                    "emailAddress": "alice@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "alice_permission_id"
                }
            ],
            "size": "0",
            "quotaBytesUsed": "0",
            "version": "8",
            "webViewLink": "https://drive.google.com/drive/folders/folder_engineering",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.google-apps.folder",
            "hasThumbnail": False,
            "thumbnailVersion": "0",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(hours=6)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": True,
            "capabilities": {
                "canAddChildren": True,
                "canChangeCopyRequiresWriterPermission": True,
                "canChangeViewersCanCopyContent": True,
                "canComment": True,
                "canCopy": True,
                "canDelete": True,
                "canDownload": True,
                "canEdit": True,
                "canListChildren": True,
                "canModifyContent": True,
                "canMoveChildrenWithinDrive": True,
                "canRename": True,
                "canShare": True,
                "canTrash": True,
                "canUntrash": False
            },
            "copyRequiresWriterPermission": False,
            "writersCanShare": True,
            "viewersCanCopyContent": False,  # More restrictive
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_engineering_team",
                    "type": "group",
                    "emailAddress": "engineering@company.com",
                    "role": "writer",
                    "displayName": "Engineering Team"
                },
                {
                    "kind": "drive#permission", 
                    "id": "permission_contractor_read",
                    "type": "user",
                    "emailAddress": "diana.contractor@company.com",
                    "role": "reader",
                    "displayName": "Diana Wilson"
                }
            ],
            "permissionIds": ["permission_engineering_team", "permission_contractor_read"],
            "isAppAuthorized": True
        },
        
        # Technical specification document
        {
            "kind": "drive#file",
            "id": "doc_tech_spec_dashboard",
            "name": "Dashboard Feature - Technical Specification",
            "mimeType": "application/vnd.google-apps.document",
            "description": "Technical specification for the new dashboard feature",
            "parents": ["folder_engineering"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=45)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(hours=3)),
            "lastModifyingUser": {
                "displayName": "Bob Smith",
                "emailAddress": "bob@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/bob-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Bob Smith",
                    "emailAddress": "bob@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "bob_permission_id"
                }
            ],
            "size": "45632",  # ~45KB document
            "quotaBytesUsed": "45632",
            "version": "23",
            "webViewLink": "https://docs.google.com/document/d/doc_tech_spec_dashboard/edit",
            "webContentLink": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=docx",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.google-apps.document",
            "hasThumbnail": True,
            "thumbnailVersion": "2",
            "thumbnailLink": "https://docs.google.com/feeds/vt?gd=true&id=doc_tech_spec_dashboard&v=2&s=AMedNnoAAAAAZL7",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(hours=1)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": False,
            "capabilities": {
                "canAddChildren": False,
                "canChangeCopyRequiresWriterPermission": False,
                "canChangeViewersCanCopyContent": False,
                "canComment": True,
                "canCopy": True,
                "canDelete": False,
                "canDownload": True,
                "canEdit": True,
                "canListChildren": False,
                "canModifyContent": True,
                "canMoveChildrenWithinDrive": False,
                "canReadRevisions": True,
                "canRename": False,
                "canShare": False,  # Only owner can share
                "canTrash": False,
                "canUntrash": False
            },
            "copyRequiresWriterPermission": True,
            "writersCanShare": False,
            "viewersCanCopyContent": False,
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_bob_owner",
                    "type": "user", 
                    "emailAddress": "bob@company.com",
                    "role": "owner",
                    "displayName": "Bob Smith"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_alice_editor",
                    "type": "user",
                    "emailAddress": "alice@company.com",
                    "role": "writer",
                    "displayName": "Alice Johnson"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_charlie_commenter",
                    "type": "user",
                    "emailAddress": "charlie@company.com", 
                    "role": "commenter",
                    "displayName": "Charlie Brown"
                }
            ],
            "permissionIds": ["permission_bob_owner", "permission_alice_editor", "permission_charlie_commenter"],
            "isAppAuthorized": True,
            "exportLinks": {
                "application/rtf": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=rtf",
                "application/vnd.oasis.opendocument.text": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=odt",
                "text/html": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=html",
                "application/pdf": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=pdf",
                "application/epub+zip": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=epub",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=docx",
                "text/plain": "https://docs.google.com/document/d/doc_tech_spec_dashboard/export?format=txt"
            }
        },
        
        # Spreadsheet with financial data (restricted access)
        {
            "kind": "drive#file",
            "id": "sheet_budget_2025",
            "name": "Budget Planning 2025",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "description": "Q4 2025 budget planning and forecasts - CONFIDENTIAL",
            "parents": ["folder_root_company"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=90)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(hours=12)),
            "lastModifyingUser": {
                "displayName": "Alice Johnson",
                "emailAddress": "alice@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/alice-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Alice Johnson",
                    "emailAddress": "alice@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "alice_permission_id"
                }
            ],
            "size": "123456",  # ~123KB
            "quotaBytesUsed": "123456",
            "version": "47",
            "webViewLink": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/edit",
            "webContentLink": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=xlsx",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.google-apps.spreadsheet",
            "hasThumbnail": True,
            "thumbnailVersion": "4",
            "thumbnailLink": "https://docs.google.com/feeds/vt?gd=true&id=sheet_budget_2025&v=4&s=AMedNnoAAAAAZL8",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(hours=12)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": True,
            "capabilities": {
                "canAddChildren": False,
                "canComment": False,  # No comments on sensitive financial data
                "canCopy": False,     # Prevent copying
                "canDelete": True,
                "canDownload": False, # Prevent download
                "canEdit": True,
                "canModifyContent": True,
                "canReadRevisions": True,
                "canRename": True,
                "canShare": True,
                "canTrash": True,
                "canUntrash": True
            },
            "copyRequiresWriterPermission": True,
            "writersCanShare": False,
            "viewersCanCopyContent": False,
            "contentRestrictions": [
                {
                    "readOnly": False,
                    "reason": "Contains sensitive financial information",
                    "restrictingUser": {
                        "displayName": "Alice Johnson",
                        "emailAddress": "alice@company.com"
                    },
                    "restrictionTime": dt_to_str(BASE_DT - timedelta(days=90)),
                    "type": "confidential"
                }
            ],
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_alice_owner",
                    "type": "user",
                    "emailAddress": "alice@company.com",
                    "role": "owner",
                    "displayName": "Alice Johnson"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_charlie_reader",
                    "type": "user",
                    "emailAddress": "charlie@company.com",
                    "role": "reader",
                    "displayName": "Charlie Brown"
                }
            ],
            "permissionIds": ["permission_alice_owner", "permission_charlie_reader"],
            "isAppAuthorized": True,
            "exportLinks": {
                "application/x-vnd.oasis.opendocument.spreadsheet": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=ods",
                "text/csv": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=csv",
                "application/pdf": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=xlsx",
                "text/tab-separated-values": "https://docs.google.com/spreadsheets/d/sheet_budget_2025/export?format=tsv"
            }
        },
        
        # Presentation file (recently shared externally)
        {
            "kind": "drive#file",
            "id": "presentation_q3_results",
            "name": "Q3 2025 Results Presentation",
            "mimeType": "application/vnd.google-apps.presentation",
            "description": "Q3 results presentation for board meeting",
            "parents": ["folder_root_company"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=14)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(hours=8)),
            "lastModifyingUser": {
                "displayName": "Charlie Brown",
                "emailAddress": "charlie@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/charlie-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Alice Johnson",
                    "emailAddress": "alice@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "alice_permission_id"
                }
            ],
            "size": "2458734",  # ~2.4MB presentation
            "quotaBytesUsed": "2458734",
            "version": "15",
            "webViewLink": "https://docs.google.com/presentation/d/presentation_q3_results/edit",
            "webContentLink": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=pptx",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.google-apps.presentation",
            "hasThumbnail": True,
            "thumbnailVersion": "3",
            "thumbnailLink": "https://docs.google.com/feeds/vt?gd=true&id=presentation_q3_results&v=3&s=AMedNnoAAAAAZL9",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(hours=2)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": True,
            "capabilities": {
                "canAddChildren": False,
                "canComment": True,
                "canCopy": True,
                "canDelete": True,
                "canDownload": True,
                "canEdit": True,
                "canModifyContent": True,
                "canReadRevisions": True,
                "canRename": True,
                "canShare": True,
                "canTrash": True,
                "canUntrash": True
            },
            "copyRequiresWriterPermission": False,
            "writersCanShare": True,
            "viewersCanCopyContent": True,
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_alice_owner",
                    "type": "user",
                    "emailAddress": "alice@company.com",
                    "role": "owner",
                    "displayName": "Alice Johnson"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_charlie_editor",
                    "type": "user",
                    "emailAddress": "charlie@company.com",
                    "role": "writer",
                    "displayName": "Charlie Brown"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_external_viewer",
                    "type": "user",
                    "emailAddress": "board.member@external.com",
                    "role": "reader",
                    "displayName": "External Board Member"
                }
            ],
            "permissionIds": ["permission_alice_owner", "permission_charlie_editor", "permission_external_viewer"],
            "isAppAuthorized": True,
            "exportLinks": {
                "application/vnd.oasis.opendocument.presentation": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=odp",
                "text/plain": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=txt",
                "application/pdf": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=pdf",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=pptx",
                "image/jpeg": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=jpeg",
                "image/png": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=png",
                "image/svg+xml": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=svg",
                "text/plain": "https://docs.google.com/presentation/d/presentation_q3_results/export?format=txt"
            }
        },
        
        # PDF file (uploaded, not Google native)
        {
            "kind": "drive#file",
            "id": "pdf_contract_techcorp",
            "name": "Partnership Contract - TechCorp.pdf",
            "mimeType": "application/pdf",
            "description": "Partnership contract with TechCorp - Legal review required",
            "parents": ["folder_root_company"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=7)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(days=7)),  # PDF not modified after upload
            "lastModifyingUser": {
                "displayName": "Alice Johnson",
                "emailAddress": "alice@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/alice-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Alice Johnson",
                    "emailAddress": "alice@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "alice_permission_id"
                }
            ],
            "size": "1245890",  # ~1.2MB PDF
            "quotaBytesUsed": "1245890",
            "version": "1",  # Never modified
            "webViewLink": "https://drive.google.com/file/d/pdf_contract_techcorp/view",
            "webContentLink": "https://drive.google.com/uc?id=pdf_contract_techcorp&export=download",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/pdf",
            "hasThumbnail": True,
            "thumbnailVersion": "1",
            "thumbnailLink": "https://docs.google.com/feeds/vt?gd=true&id=pdf_contract_techcorp&v=1&s=AMedNnoAAAAAZLA",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(days=1)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": True,
            "capabilities": {
                "canAddChildren": False,
                "canComment": True,
                "canCopy": False,  # Legal document - no copying
                "canDelete": True,
                "canDownload": False,  # Prevent download outside organization
                "canEdit": False,  # PDF cannot be edited in Drive
                "canModifyContent": False,
                "canReadRevisions": False,
                "canRename": True,
                "canShare": True,
                "canTrash": True,
                "canUntrash": True
            },
            "copyRequiresWriterPermission": True,
            "writersCanShare": False,
            "viewersCanCopyContent": False,
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_alice_owner",
                    "type": "user",
                    "emailAddress": "alice@company.com",
                    "role": "owner",
                    "displayName": "Alice Johnson"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_legal_reader",
                    "type": "group",
                    "emailAddress": "legal@company.com",
                    "role": "reader",
                    "displayName": "Legal Team"
                }
            ],
            "permissionIds": ["permission_alice_owner", "permission_legal_reader"],
            "isAppAuthorized": True,
            "md5Checksum": "d85b1213473c2fd7c2045020a6b9c62c",
            "sha1Checksum": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "sha256Checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        
        # Image file (design asset)
        {
            "kind": "drive#file",
            "id": "img_logo_variants",
            "name": "Company Logo Variants.png",
            "mimeType": "image/png",
            "description": "Company logo variants for different use cases",
            "parents": ["folder_root_company"],
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=120)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(days=30)),
            "lastModifyingUser": {
                "displayName": "Frank Miller",
                "emailAddress": "frank@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/frank-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Frank Miller",
                    "emailAddress": "frank@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "frank_permission_id"
                }
            ],
            "size": "567890",  # ~550KB image
            "quotaBytesUsed": "567890",
            "version": "3",
            "webViewLink": "https://drive.google.com/file/d/img_logo_variants/view",
            "webContentLink": "https://drive.google.com/uc?id=img_logo_variants&export=download",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/image/png",
            "hasThumbnail": True,
            "thumbnailVersion": "3",
            "thumbnailLink": "https://docs.google.com/feeds/vt?gd=true&id=img_logo_variants&v=3&s=AMedNnoAAAAAZLB",
            "viewedByMe": True,
            "viewedByMeTime": dt_to_str(BASE_DT - timedelta(days=5)),
            "sharedWithMeTime": None,
            "sharingUser": None,
            "shared": True,
            "ownedByMe": False,
            "capabilities": {
                "canAddChildren": False,
                "canComment": True,
                "canCopy": True,
                "canDelete": False,  # Don't delete design assets
                "canDownload": True,
                "canEdit": False,  # Image files can't be edited in Drive
                "canModifyContent": False,
                "canReadRevisions": True,
                "canRename": False,
                "canShare": True,
                "canTrash": False,
                "canUntrash": False
            },
            "copyRequiresWriterPermission": False,
            "writersCanShare": True,
            "viewersCanCopyContent": True,
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_frank_owner",
                    "type": "user",
                    "emailAddress": "frank@company.com",
                    "role": "owner",
                    "displayName": "Frank Miller"
                },
                {
                    "kind": "drive#permission",
                    "id": "permission_marketing_reader",
                    "type": "group",
                    "emailAddress": "marketing@company.com",
                    "role": "reader",
                    "displayName": "Marketing Team"
                }
            ],
            "permissionIds": ["permission_frank_owner", "permission_marketing_reader"],
            "isAppAuthorized": True,
            "imageMediaMetadata": {
                "width": 2048,
                "height": 1024,
                "rotation": 0,
                "time": dt_to_str(BASE_DT - timedelta(days=120)),
                "location": {}
            },
            "md5Checksum": "a1b2c3d4e5f6789012345678901234567890abcd",
            "sha1Checksum": "1234567890abcdef1234567890abcdef12345678",
            "sha256Checksum": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        },
        
        # Trashed file (recently deleted)
        {
            "kind": "drive#file",
            "id": "doc_old_spec_deleted",
            "name": "Old Feature Spec (DEPRECATED).docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "description": "Old feature specification - replaced by new version",
            "parents": [],  # Trashed files have no parent
            "trashed": True,
            "trashedTime": dt_to_str(BASE_DT - timedelta(days=2)),
            "trashingUser": {
                "displayName": "Bob Smith",
                "emailAddress": "bob@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/bob-photo=s64"
            },
            "driveId": "company_shared_drive",
            "createdTime": dt_to_str(BASE_DT - timedelta(days=180)),
            "modifiedTime": dt_to_str(BASE_DT - timedelta(days=60)),
            "lastModifyingUser": {
                "displayName": "Bob Smith",
                "emailAddress": "bob@company.com",
                "photoLink": "https://lh3.googleusercontent.com/a/bob-photo=s64"
            },
            "owners": [
                {
                    "displayName": "Bob Smith",
                    "emailAddress": "bob@company.com",
                    "kind": "drive#user",
                    "me": False,
                    "permissionId": "bob_permission_id"
                }
            ],
            "size": "234567",
            "quotaBytesUsed": "234567",
            "version": "12",
            "webViewLink": "https://drive.google.com/file/d/doc_old_spec_deleted/view",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "hasThumbnail": False,
            "thumbnailVersion": "0",
            "viewedByMe": False,
            "shared": False,
            "ownedByMe": False,
            "capabilities": {
                "canAddChildren": False,
                "canComment": False,
                "canCopy": False,
                "canDelete": True,  # Permanent deletion from trash
                "canDownload": False,
                "canEdit": False,
                "canModifyContent": False,
                "canReadRevisions": False,
                "canRename": False,
                "canShare": False,
                "canTrash": False,  # Already trashed
                "canUntrash": True   # Can be restored
            },
            "permissions": [
                {
                    "kind": "drive#permission",
                    "id": "permission_bob_owner",
                    "type": "user",
                    "emailAddress": "bob@company.com",
                    "role": "owner",
                    "displayName": "Bob Smith"
                }
            ],
            "permissionIds": ["permission_bob_owner"],
            "isAppAuthorized": True
        }
    ]

def get_mock_drive_changes() -> List[Dict[str, Any]]:
    """
    Mock Drive API changes for testing change detection.
    Shows various types of changes: create, modify, delete, permission changes.
    """
    
    def dt_to_str(dt):
        return dt.isoformat() + "Z"
    
    return [
        # File created
        {
            "kind": "drive#change",
            "changeType": "file",
            "time": dt_to_str(BASE_DT - timedelta(hours=3)),
            "removed": False,
            "fileId": "doc_tech_spec_dashboard",
            "file": {
                "id": "doc_tech_spec_dashboard",
                "name": "Dashboard Feature - Technical Specification",
                "mimeType": "application/vnd.google-apps.document"
            },
            "changeDetails": {
                "changeType": "modify",
                "previousVersion": "22",
                "currentVersion": "23",
                "modifiedBy": "bob@company.com",
                "modificationDetails": "Content updated - added API specifications"
            }
        },
        
        # Permission added
        {
            "kind": "drive#change",
            "changeType": "permission",
            "time": dt_to_str(BASE_DT - timedelta(hours=8)),
            "removed": False,
            "fileId": "presentation_q3_results",
            "file": {
                "id": "presentation_q3_results",
                "name": "Q3 2025 Results Presentation",
                "mimeType": "application/vnd.google-apps.presentation"
            },
            "changeDetails": {
                "changeType": "permission_add",
                "permissionId": "permission_external_viewer",
                "addedPermission": {
                    "type": "user",
                    "emailAddress": "board.member@external.com",
                    "role": "reader",
                    "displayName": "External Board Member"
                },
                "grantedBy": "alice@company.com"
            }
        },
        
        # File deleted (moved to trash)
        {
            "kind": "drive#change",
            "changeType": "file",
            "time": dt_to_str(BASE_DT - timedelta(days=2)),
            "removed": True,
            "fileId": "doc_old_spec_deleted",
            "file": {
                "id": "doc_old_spec_deleted",
                "name": "Old Feature Spec (DEPRECATED).docx",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "trashed": True
            },
            "changeDetails": {
                "changeType": "trash",
                "trashedBy": "bob@company.com",
                "trashTime": dt_to_str(BASE_DT - timedelta(days=2)),
                "reason": "Replaced by new technical specification"
            }
        },
        
        # File renamed
        {
            "kind": "drive#change", 
            "changeType": "file",
            "time": dt_to_str(BASE_DT - timedelta(days=30)),
            "removed": False,
            "fileId": "img_logo_variants",
            "file": {
                "id": "img_logo_variants",
                "name": "Company Logo Variants.png",
                "mimeType": "image/png"
            },
            "changeDetails": {
                "changeType": "rename",
                "previousName": "Logo Options v2.png",
                "currentName": "Company Logo Variants.png",
                "renamedBy": "frank@company.com"
            }
        },
        
        # Permission removed
        {
            "kind": "drive#change",
            "changeType": "permission",
            "time": dt_to_str(BASE_DT - timedelta(days=60)),
            "removed": True,
            "fileId": "sheet_budget_2025",
            "file": {
                "id": "sheet_budget_2025",
                "name": "Budget Planning 2025",
                "mimeType": "application/vnd.google-apps.spreadsheet"
            },
            "changeDetails": {
                "changeType": "permission_remove",
                "permissionId": "permission_eve_editor",
                "removedPermission": {
                    "type": "user",
                    "emailAddress": "eve@company.com",
                    "role": "writer",
                    "displayName": "Eve Davis"
                },
                "removedBy": "alice@company.com",
                "removalReason": "Access no longer needed - role change"
            }
        },
        
        # New folder created
        {
            "kind": "drive#change",
            "changeType": "file",
            "time": dt_to_str(BASE_DT - timedelta(days=7)),
            "removed": False,
            "fileId": "folder_marketing_new",
            "file": {
                "id": "folder_marketing_new",
                "name": "Marketing Materials",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["folder_root_company"]
            },
            "changeDetails": {
                "changeType": "create",
                "createdBy": "eve@company.com",
                "parentFolder": "folder_root_company"
            }
        }
    ]

def get_mock_permission_changes() -> List[Dict[str, Any]]:
    """Mock permission changes for audit trail."""
    
    def dt_to_str(dt):
        return dt.isoformat() + "Z"
        
    return [
        {
            "permissionId": "permission_external_viewer",
            "fileId": "presentation_q3_results",
            "fileName": "Q3 2025 Results Presentation",
            "changeType": "grant",
            "grantedTo": {
                "type": "user",
                "emailAddress": "board.member@external.com",
                "displayName": "External Board Member"
            },
            "role": "reader",
            "grantedBy": {
                "emailAddress": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "grantTime": dt_to_str(BASE_DT - timedelta(hours=8)),
            "expirationTime": dt_to_str(BASE_DT + timedelta(days=7)),  # Expires in 1 week
            "allowFileDiscovery": False,
            "sendNotificationEmail": True,
            "grantReason": "Board meeting presentation access"
        },
        
        {
            "permissionId": "permission_contractor_read",
            "fileId": "folder_engineering",
            "fileName": "Engineering",
            "changeType": "grant",
            "grantedTo": {
                "type": "user",
                "emailAddress": "diana.contractor@company.com",
                "displayName": "Diana Wilson"
            },
            "role": "reader",
            "grantedBy": {
                "emailAddress": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "grantTime": dt_to_str(BASE_DT - timedelta(days=180)),
            "expirationTime": dt_to_str(BASE_DT + timedelta(days=5)),  # Expires soon
            "allowFileDiscovery": False,
            "sendNotificationEmail": True,
            "grantReason": "Contractor access to engineering documents"
        },
        
        {
            "permissionId": "permission_eve_editor",
            "fileId": "sheet_budget_2025",
            "fileName": "Budget Planning 2025",
            "changeType": "revoke",
            "revokedFrom": {
                "type": "user", 
                "emailAddress": "eve@company.com",
                "displayName": "Eve Davis"
            },
            "role": "writer",
            "revokedBy": {
                "emailAddress": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "revokeTime": dt_to_str(BASE_DT - timedelta(days=60)),
            "originalGrantTime": dt_to_str(BASE_DT - timedelta(days=150)),
            "revokeReason": "Department change - no longer needs budget access"
        }
    ]

def get_mock_api_errors() -> Dict[str, Any]:
    """Mock Drive API errors for testing error handling."""
    return {
        "insufficient_permissions": {
            "error": {
                "code": 403,
                "message": "Insufficient Permission: Request had insufficient authentication scopes.",
                "status": "PERMISSION_DENIED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
                        "domain": "googleapis.com",
                        "metadata": {
                            "service": "drive.googleapis.com",
                            "method": "drive.files.get"
                        }
                    }
                ]
            }
        },
        
        "file_not_found": {
            "error": {
                "code": 404,
                "message": "File not found",
                "status": "NOT_FOUND"
            }
        },
        
        "rate_limit_exceeded": {
            "error": {
                "code": 429,
                "message": "Rate Limit Exceeded",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "60s"
                    }
                ]
            }
        },
        
        "storage_quota_exceeded": {
            "error": {
                "code": 403,
                "message": "The user's Drive storage quota has been exceeded.",
                "status": "PERMISSION_DENIED"
            }
        }
    }

def get_mock_privacy_filters() -> Dict[str, Any]:
    """Mock privacy filters for testing privacy compliance."""
    return {
        "exclude_patterns": [
            "**/Personal/**",
            "**/Private/**",
            "**/*_CONFIDENTIAL*",
            "**/*_PERSONAL*"
        ],
        "include_patterns": [
            "**/Company Documents/**",
            "**/Engineering/**", 
            "**/Product/**",
            "**/Marketing/**"
        ],
        "restricted_mimetypes": [
            "application/x-unknown",  # Unknown file types
            "application/octet-stream"  # Binary files without clear type
        ],
        "external_sharing_policy": {
            "block_external_domains": [
                "competitor1.com",
                "competitor2.com"
            ],
            "allow_external_domains": [
                "partner.com",
                "trusted-vendor.com"
            ],
            "require_approval_for_external": True,
            "max_external_access_days": 30
        }
    }

# Helper functions
def validate_mock_drive_data():
    """Validate that all mock drive data is well-formed and privacy-compliant."""
    try:
        files = get_mock_drive_files()
        changes = get_mock_drive_changes()
        permission_changes = get_mock_permission_changes()
        
        # Validate JSON serializability
        json.dumps(files)
        json.dumps(changes)
        json.dumps(permission_changes)
        
        # Privacy compliance checks
        for file_item in files:
            # Ensure no file content is stored
            assert "content" not in file_item
            assert "body" not in file_item
            assert "text_content" not in file_item
            
            # Required metadata fields
            assert "id" in file_item
            assert "name" in file_item
            assert "mimeType" in file_item
            assert "createdTime" in file_item
            assert "modifiedTime" in file_item
            
            # Permission structure
            if "permissions" in file_item:
                for permission in file_item["permissions"]:
                    assert "role" in permission
                    assert permission["role"] in ["owner", "writer", "commenter", "reader"]
        
        return True
    except Exception as e:
        print(f"Drive mock data validation failed: {e}")
        return False

def get_mock_collection_result() -> Dict[str, Any]:
    """Mock result from drive collector matching expected format."""
    files = get_mock_drive_files()
    active_files = [f for f in files if not f.get("trashed", False)]
    
    return {
        "discovered": {
            "total_files": len(files),
            "active_files": len(active_files),
            "trashed_files": len([f for f in files if f.get("trashed", False)]),
            "folders": len([f for f in files if f["mimeType"] == "application/vnd.google-apps.folder"]),
            "shared_files": len([f for f in files if f.get("shared", False)]),
            "external_shares": len([f for f in files if any(
                p.get("emailAddress", "").split("@")[1] != "company.com" 
                for p in f.get("permissions", []) 
                if p.get("emailAddress")
            )])
        },
        "collected": {
            "metadata_records": len(active_files),
            "permission_records": sum(len(f.get("permissions", [])) for f in active_files),
            "change_records": len(get_mock_drive_changes()),
            "audit_events": len(get_mock_permission_changes()),
            "content_bytes_stored": 0  # Privacy compliance - no content stored
        },
        "files": files,
        "changes": get_mock_drive_changes(),
        "permission_changes": get_mock_permission_changes(),
        "privacy_filters": get_mock_privacy_filters(),
        "metadata": {
            "collection_time": BASE_DT.isoformat(),
            "privacy_compliant": True,
            "content_excluded": True,
            "audit_trail_complete": True
        }
    }

# Ensure data is valid on import
if __name__ == "__main__":
    assert validate_mock_drive_data(), "Drive mock data validation failed"
    print("All Drive mock data validated successfully!")
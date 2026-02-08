"""
Google Drive Service for LHIMS Backup System

This module handles all Google Drive operations including authentication,
file uploads, folder management, and backup organization.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveService:
    """Service class for Google Drive operations."""
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        """
        Initialize Google Drive service.
        
        Args:
            credentials_path: Path to OAuth2 credentials file
            token_path: Path to store OAuth2 token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.authenticate()
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            creds = None
            
            # Load existing token if available
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                logger.info("Loaded existing credentials from token file")
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                else:
                    # Run OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Completed OAuth authentication flow")
                
                # Save credentials for next run
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved credentials to {self.token_path}")
            
            # Build the service
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: ID of parent folder (optional)
            
        Returns:
            Folder ID if created successfully, None otherwise
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder '{folder_name}': {str(e)}")
            return None
    
    def find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find existing folder or create new one.
        
        Args:
            folder_name: Name of the folder
            parent_id: ID of parent folder (optional)
            
        Returns:
            Folder ID if found or created, None otherwise
        """
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"Found existing folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            else:
                # Create new folder if not found
                return self.create_folder(folder_name, parent_id)
                
        except HttpError as e:
            logger.error(f"Error finding/creating folder '{folder_name}': {str(e)}")
            return None
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None, 
                   overwrite: bool = False) -> Optional[str]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Local path to file
            folder_id: ID of folder to upload to (optional)
            overwrite: Whether to overwrite existing file
            
        Returns:
            File ID if upload successful, None otherwise
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            logger.info(f"Uploading '{file_name}' ({file_size} bytes)")
            
            # Check if file already exists (if overwrite is False)
            if not overwrite:
                query = f"name='{file_name}'"
                if folder_id:
                    query += f" and '{folder_id}' in parents"
                
                results = self.service.files().list(q=query).execute()
                existing_files = results.get('files', [])
                
                if existing_files:
                    logger.warning(f"File '{file_name}' already exists. Skipping upload.")
                    return existing_files[0]['id']
            
            # Prepare file metadata
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media upload object
            media = MediaFileUpload(str(file_path), resumable=True)
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded '{file_name}' with ID: {file_id}")
            return file_id
            
        except HttpError as e:
            logger.error(f"Error uploading file '{file_path}': {str(e)}")
            return None
    
    def setup_backup_structure(self, base_folder_name: str = "LHIMS Backups") -> Dict[str, str]:
        """
        Create the backup folder structure in Google Drive.
        
        Args:
            base_folder_name: Name of the main backup folder
            
        Returns:
            Dictionary with folder IDs
        """
        try:
            # Create main backup folder
            main_folder_id = self.find_or_create_folder(base_folder_name)
            if not main_folder_id:
                raise Exception("Failed to create main backup folder")
            
            # Create year folder
            current_year = datetime.now().strftime("%Y")
            year_folder_id = self.find_or_create_folder(current_year, main_folder_id)
            if not year_folder_id:
                raise Exception("Failed to create year folder")
            
            # Create month folder
            current_month = datetime.now().strftime("%m-%B")
            month_folder_id = self.find_or_create_folder(current_month, year_folder_id)
            if not month_folder_id:
                raise Exception("Failed to create month folder")
            
            folder_structure = {
                'main': main_folder_id,
                'year': year_folder_id,
                'month': month_folder_id
            }
            
            logger.info(f"Backup folder structure created: {folder_structure}")
            return folder_structure
            
        except Exception as e:
            logger.error(f"Error setting up backup structure: {str(e)}")
            return {}
    
    def cleanup_old_backups(self, folder_id: str, days_to_keep: int = 30) -> bool:
        """
        Delete old backup files from Google Drive.
        
        Args:
            folder_id: ID of folder to clean
            days_to_keep: Number of days to keep files
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            # List all files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields='files(id, name, createdTime)'
            ).execute()
            
            files = results.get('files', [])
            deleted_count = 0
            
            for file in files:
                created_time = datetime.fromisoformat(
                    file['createdTime'].replace('Z', '+00:00')
                ).timestamp()
                
                if created_time < cutoff_date:
                    self.service.files().delete(fileId=file['id']).execute()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {file['name']}")
            
            logger.info(f"Cleanup completed. Deleted {deleted_count} old files.")
            return True
            
        except HttpError as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get Google Drive storage information.
        
        Returns:
            Dictionary with storage details
        """
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            storage_quota = about.get('storageQuota', {})
            
            return {
                'limit': int(storage_quota.get('limit', 0)),
                'usage': int(storage_quota.get('usage', 0)),
                'usage_in_drive': int(storage_quota.get('usageInDrive', 0)),
                'usage_in_drive_trash': int(storage_quota.get('usageInDriveTrash', 0))
            }
            
        except HttpError as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return {}


if __name__ == "__main__":
    # Test the Google Drive service
    drive_service = GoogleDriveService()
    
    if drive_service.service:
        print("✅ Google Drive authentication successful!")
        
        # Test folder creation
        folder_structure = drive_service.setup_backup_structure()
        if folder_structure:
            print(f"✅ Backup folders created: {folder_structure}")
        
        # Get storage info
        storage_info = drive_service.get_storage_info()
        if storage_info:
            usage_mb = storage_info.get('usage', 0) / (1024 * 1024)
            limit_mb = storage_info.get('limit', 0) / (1024 * 1024)
            print(f"📊 Storage usage: {usage_mb:.1f} MB / {limit_mb:.1f} MB")
    else:
        print("❌ Google Drive authentication failed!")

"""
Authentication Manager - Handle credentials for private repositories.

This module provides credential management for accessing private
Maven repositories and other authenticated download sources.
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class AuthManager:
    """Manages authentication credentials for private repositories."""

    def __init__(self):
        self.config_dir = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
        self.auth_file = os.path.join(self.config_dir, "auth.json")
        os.makedirs(self.config_dir, exist_ok=True)
        self._initialize_auth_storage()

    def _initialize_auth_storage(self):
        """Initialize the authentication storage file if it doesn't exist."""
        if not os.path.exists(self.auth_file):
            with open(self.auth_file, "w") as f:
                json.dump({}, f)

    def save_credential(self, repo_url: str, username: str, password: str) -> bool:
        """
        Save authentication credentials for a repository.
        
        Args:
            repo_url: The repository URL
            username: The username for authentication
            password: The password/api key for authentication
            
        Returns:
            True if credentials were saved successfully, False otherwise
        """
        try:
            # Normalize URL to remove trailing slashes
            normalized_url = repo_url.rstrip('/')
            
            # Load existing credentials
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)
            
            # Store credentials (in a real implementation, these would be encrypted)
            auth_data[normalized_url] = {
                "username": username,
                "password": password
            }
            
            # Save credentials
            with open(self.auth_file, "w") as f:
                json.dump(auth_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    def get_credential(self, repo_url: str) -> Optional[Tuple[str, str]]:
        """
        Get authentication credentials for a repository.
        
        Args:
            repo_url: The repository URL
            
        Returns:
            Tuple of (username, password) if found, None otherwise
        """
        try:
            # Normalize URL to remove trailing slashes
            normalized_url = repo_url.rstrip('/')
            
            # Load credentials
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)
            
            if normalized_url in auth_data:
                data = auth_data[normalized_url]
                return data["username"], data["password"]
            
            return None
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None

    def remove_credential(self, repo_url: str) -> bool:
        """
        Remove authentication credentials for a repository.
        
        Args:
            repo_url: The repository URL
            
        Returns:
            True if credentials were removed successfully, False otherwise
        """
        try:
            # Normalize URL to remove trailing slashes
            normalized_url = repo_url.rstrip('/')
            
            # Load existing credentials
            with open(self.auth_file, "r") as f:
                auth_data = json.load(f)
            
            # Remove credentials if they exist
            if normalized_url in auth_data:
                del auth_data[normalized_url]
            
            # Save updated credentials
            with open(self.auth_file, "w") as f:
                json.dump(auth_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error removing credentials: {e}")
            return False

    def get_auth_header(self, repo_url: str) -> Optional[Dict[str, str]]:
        """
        Get authentication headers for a repository.
        
        Args:
            repo_url: The repository URL
            
        Returns:
            Dictionary with authorization header if credentials exist, None otherwise
        """
        creds = self.get_credential(repo_url)
        if creds:
            username, password = creds
            # Create Basic Auth header
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}"
            }
        return None


# Global instance
auth_manager = AuthManager()


def save_repository_credential(repo_url: str, username: str, password: str) -> bool:
    """
    Save authentication credentials for a repository.
    
    Args:
        repo_url: The repository URL
        username: The username for authentication
        password: The password/api key for authentication
        
    Returns:
        True if credentials were saved successfully, False otherwise
    """
    return auth_manager.save_credential(repo_url, username, password)


def get_repository_credential(repo_url: str) -> Optional[Tuple[str, str]]:
    """
    Get authentication credentials for a repository.
    
    Args:
        repo_url: The repository URL
        
    Returns:
        Tuple of (username, password) if found, None otherwise
    """
    return auth_manager.get_credential(repo_url)


def remove_repository_credential(repo_url: str) -> bool:
    """
    Remove authentication credentials for a repository.
    
    Args:
        repo_url: The repository URL
        
    Returns:
        True if credentials were removed successfully, False otherwise
    """
    return auth_manager.remove_credential(repo_url)


def get_auth_headers(repo_url: str) -> Optional[Dict[str, str]]:
    """
    Get authentication headers for a repository.
    
    Args:
        repo_url: The repository URL
        
    Returns:
        Dictionary with authorization header if credentials exist, None otherwise
    """
    return auth_manager.get_auth_header(repo_url)
#!/usr/bin/env python3
"""
Unified configuration management for Sync Toolkit.
Handles interactive credential prompts and configuration storage.
"""
import os
import json
import getpass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class SyncConfig:
    """Configuration for Sync.so API"""
    api_key: Optional[str] = None
    api_url: str = "https://api.sync.so/v2"
    
@dataclass
class StorageConfig:
    """Configuration for storage backends"""
    # Supabase
    supabase_host: Optional[str] = None
    supabase_bucket: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # AWS S3
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_base_path: Optional[str] = None

@dataclass
class ToolkitConfig:
    """Main toolkit configuration"""
    sync: SyncConfig
    storage: StorageConfig
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "sync": asdict(self.sync),
            "storage": asdict(self.storage)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolkitConfig":
        """Create from dictionary"""
        return cls(
            sync=SyncConfig(**data.get("sync", {})),
            storage=StorageConfig(**data.get("storage", {}))
        )


class ConfigManager:
    """Manages toolkit configuration with interactive prompts"""
    
    CONFIG_FILE = Path.home() / ".sync-toolkit" / "config.json"
    
    def __init__(self):
        self.config: Optional[ToolkitConfig] = None
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions
        self.CONFIG_FILE.parent.chmod(0o700)
    
    def load(self) -> ToolkitConfig:
        """Load configuration from file"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                self.config = ToolkitConfig.from_dict(data)
                return self.config
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        
        # Return empty config if file doesn't exist or is invalid
        self.config = ToolkitConfig(
            sync=SyncConfig(),
            storage=StorageConfig()
        )
        return self.config
    
    def save(self, config: Optional[ToolkitConfig] = None):
        """Save configuration to file"""
        if config:
            self.config = config
        
        if not self.config:
            return
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            # Set restrictive permissions
            self.CONFIG_FILE.chmod(0o600)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def get_sync_api_key(self, prompt: bool = True) -> Optional[str]:
        """Get Sync API key, prompting if needed"""
        config = self.load()
        
        if config.sync.api_key:
            return config.sync.api_key
        
        if prompt:
            print("\n" + "="*60)
            print("Sync.so API Configuration")
            print("="*60)
            api_key = getpass.getpass("Enter your Sync.so API key (hidden): ").strip()
            
            if api_key:
                config.sync.api_key = api_key
                self.save(config)
                return api_key
        
        return None
    
    def get_supabase_config(self, prompt: bool = True) -> StorageConfig:
        """Get Supabase configuration, prompting if needed"""
        config = self.load()
        storage = config.storage
        
        needs_prompt = not all([
            storage.supabase_host,
            storage.supabase_bucket,
            storage.supabase_key
        ])
        
        if needs_prompt and prompt:
            print("\n" + "="*60)
            print("Supabase Storage Configuration")
            print("="*60)
            
            if not storage.supabase_host:
                host = input("Supabase project host (e.g., https://xyz.supabase.co): ").strip()
                if host:
                    storage.supabase_host = host
            
            if not storage.supabase_bucket:
                bucket = input("Supabase storage bucket name: ").strip()
                if bucket:
                    storage.supabase_bucket = bucket
            
            if not storage.supabase_key:
                key = getpass.getpass("Supabase service role key (hidden): ").strip()
                if key:
                    storage.supabase_key = key
            
            config.storage = storage
            self.save(config)
        
        return storage
    
    def get_aws_config(self, prompt: bool = True) -> StorageConfig:
        """Get AWS configuration, prompting if needed"""
        config = self.load()
        storage = config.storage
        
        # Check if AWS credentials are available via boto3 default chain
        try:
            import boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials:
                # Use default credentials if available
                return storage
        except ImportError:
            pass
        
        needs_prompt = not all([
            storage.aws_access_key_id,
            storage.aws_secret_access_key
        ])
        
        if needs_prompt and prompt:
            print("\n" + "="*60)
            print("AWS S3 Configuration")
            print("="*60)
            print("Note: AWS credentials can also be set via:")
            print("  - AWS CLI: aws configure")
            print("  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("  - IAM role (if running on EC2)")
            print()
            
            use_env = input("Use AWS credentials from environment/IAM? (Y/n): ").strip().lower()
            if use_env != 'n':
                return storage
            
            if not storage.aws_access_key_id:
                access_key = input("AWS Access Key ID: ").strip()
                if access_key:
                    storage.aws_access_key_id = access_key
            
            if not storage.aws_secret_access_key:
                secret_key = getpass.getpass("AWS Secret Access Key (hidden): ").strip()
                if secret_key:
                    storage.aws_secret_access_key = secret_key
            
            if not storage.aws_region:
                region = input(f"AWS Region [{storage.aws_region}]: ").strip()
                if region:
                    storage.aws_region = region
            
            config.storage = storage
            self.save(config)
        
        return storage
    
    def get_s3_config(self, prompt: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """Get S3 bucket and base path, prompting if needed"""
        config = self.load()
        storage = config.storage
        
        needs_prompt = not storage.s3_bucket or not storage.s3_base_path
        
        if needs_prompt and prompt:
            print("\n" + "="*60)
            print("S3 Storage Configuration")
            print("="*60)
            
            if not storage.s3_bucket:
                bucket = input("S3 bucket name: ").strip()
                if bucket:
                    storage.s3_bucket = bucket
            
            if not storage.s3_base_path:
                base_path = input("S3 base path (e.g., generations/uuid): ").strip()
                if base_path:
                    storage.s3_base_path = base_path
            
            config.storage = storage
            self.save(config)
        
        return storage.s3_bucket, storage.s3_base_path
    
    def clear_credentials(self):
        """Clear stored credentials (for security)"""
        config = self.load()
        config.sync.api_key = None
        config.storage.supabase_key = None
        config.storage.aws_access_key_id = None
        config.storage.aws_secret_access_key = None
        self.save(config)
        print("Credentials cleared from config file.")


# Global instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get global config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


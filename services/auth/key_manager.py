"""
Persistent key management with file-based storage

This module manages cryptographic keys with persistent storage:
- Master key generation and loading
- Key derivation for specific purposes
- Automatic key rotation
- Secure file permissions

Keys are stored in the keys/ directory with strict permissions (0o600).
"""
import os
import threading
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

from core.security import CryptoManager


class KeyManager:
    """
    Manages persistent cryptographic keys
    
    Features:
    - Master key generation and persistence
    - Purpose-specific key derivation
    - Automatic key rotation
    - Thread-safe operations
    - Secure file permissions
    """
    
    def __init__(self, keys_dir: str = "keys"):
        """
        Initialize key manager
        
        Args:
            keys_dir: Directory for key storage (default: "keys")
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.chmod(0o700)  # Owner read/write/execute only
        
        self._master_key: Optional[bytes] = None
        self._derived_keys: Dict[str, bytes] = {}
        self._lock = threading.Lock()
        
        # Load or generate master key
        self._ensure_master_key()
    
    def _ensure_master_key(self):
        """Ensure master key exists (load or generate)"""
        master_key_path = self.keys_dir / "master.key"
        
        if master_key_path.exists():
            # Load existing master key
            with self._lock:
                self._master_key = master_key_path.read_bytes()
                print(f"✅ Master key loaded from {master_key_path}")
        else:
            # Generate new master key
            with self._lock:
                self._master_key = CryptoManager.generate_salt(32)
                master_key_path.write_bytes(self._master_key)
                master_key_path.chmod(0o600)  # Owner read/write only
                print(f"🔑 Master key generated and saved to {master_key_path}")
    
    def get_master_key(self) -> bytes:
        """
        Get the master key
        
        Returns:
            bytes: Master key (32 bytes)
        """
        with self._lock:
            if self._master_key is None:
                raise RuntimeError("Master key not initialized")
            return self._master_key
    
    def derive_key(self, purpose: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive a purpose-specific key from the master key
        
        Args:
            purpose: Key purpose (e.g., "database", "cache", "backup")
            salt: Optional salt (generated if not provided)
        
        Returns:
            bytes: Derived key (32 bytes)
        
        Example:
            >>> km = KeyManager()
            >>> db_key = km.derive_key("database")
            >>> len(db_key)
            32
        """
        # Check cache
        if purpose in self._derived_keys:
            return self._derived_keys[purpose]
        
        # Generate salt if not provided
        if salt is None:
            salt = CryptoManager.generate_salt()
        
        # Derive key
        master_key_str = self.get_master_key().hex()
        derived_key = CryptoManager.derive_key(
            f"{master_key_str}:{purpose}",
            salt,
            iterations=100_000  # Fewer iterations for derived keys
        )
        
        # Cache
        with self._lock:
            self._derived_keys[purpose] = derived_key
        
        return derived_key
    
    def rotate_master_key(self) -> bytes:
        """
        Rotate the master key (generate new one)
        
        Returns:
            bytes: New master key
        
        Warning:
            This will invalidate all encrypted data!
            Ensure data is re-encrypted with the new key.
        """
        # Backup old key
        old_key_path = self.keys_dir / f"master.key.backup.{int(datetime.now().timestamp())}"
        master_key_path = self.keys_dir / "master.key"
        
        if master_key_path.exists():
            old_key_path.write_bytes(master_key_path.read_bytes())
            old_key_path.chmod(0o600)
            print(f"📦 Old master key backed up to {old_key_path}")
        
        # Generate new key
        with self._lock:
            self._master_key = CryptoManager.generate_salt(32)
            master_key_path.write_bytes(self._master_key)
            master_key_path.chmod(0o600)
            
            # Clear derived keys cache
            self._derived_keys.clear()
        
        print(f"🔄 Master key rotated")
        return self._master_key
    
    def save_key(self, name: str, key: bytes) -> Path:
        """
        Save a key to a file
        
        Args:
            name: Key name (filename)
            key: Key bytes
        
        Returns:
            Path: Path to saved key file
        """
        key_path = self.keys_dir / f"{name}.key"
        
        with self._lock:
            key_path.write_bytes(key)
            key_path.chmod(0o600)
        
        return key_path
    
    def load_key(self, name: str) -> Optional[bytes]:
        """
        Load a key from a file
        
        Args:
            name: Key name (filename without .key extension)
        
        Returns:
            bytes: Key bytes or None if not found
        """
        key_path = self.keys_dir / f"{name}.key"
        
        if not key_path.exists():
            return None
        
        return key_path.read_bytes()
    
    def delete_key(self, name: str) -> bool:
        """
        Delete a key file
        
        Args:
            name: Key name
        
        Returns:
            bool: True if deleted, False if not found
        """
        key_path = self.keys_dir / f"{name}.key"
        
        if not key_path.exists():
            return False
        
        with self._lock:
            # Overwrite with random data before deletion (secure delete)
            size = key_path.stat().st_size
            key_path.write_bytes(os.urandom(size))
            key_path.unlink()
        
        return True
    
    def list_keys(self) -> list:
        """
        List all key files
        
        Returns:
            list: List of key names (without .key extension)
        """
        return [
            p.stem
            for p in self.keys_dir.glob("*.key")
            if p.is_file() and not p.name.startswith(".")
        ]
    
    def export_public_key(self, name: str = "jwt_public") -> Optional[bytes]:
        """
        Export a public key (for RSA keys)
        
        Args:
            name: Key name
        
        Returns:
            bytes: Public key PEM or None if not found
        """
        public_key_path = self.keys_dir / f"{name}.pem"
        
        if not public_key_path.exists():
            return None
        
        return public_key_path.read_bytes()
    
    def generate_rsa_keys(self, name: str = "jwt") -> tuple:
        """
        Generate and save RSA key pair
        
        Args:
            name: Base name for key files
        
        Returns:
            tuple: (private_key_pem, public_key_pem)
        """
        # Generate keys
        private_pem, public_pem = CryptoManager.generate_rsa_keypair()
        
        # Save keys
        private_path = self.keys_dir / f"{name}_private.pem"
        public_path = self.keys_dir / f"{name}_public.pem"
        
        with self._lock:
            private_path.write_bytes(private_pem)
            private_path.chmod(0o600)
            
            public_path.write_bytes(public_pem)
            public_path.chmod(0o644)  # Public key can be readable
        
        print(f"🔐 RSA keys generated:")
        print(f"  Private: {private_path}")
        print(f"  Public:  {public_path}")
        
        return private_pem, public_pem


# Singleton instance
_key_manager: Optional[KeyManager] = None
_key_manager_lock = threading.Lock()


def get_key_manager(keys_dir: str = "keys") -> KeyManager:
    """
    Get the key manager singleton (thread-safe)
    
    Args:
        keys_dir: Directory for key storage
    
    Returns:
        KeyManager: Singleton instance
    """
    global _key_manager
    
    # Fast path
    if _key_manager is not None:
        return _key_manager
    
    # Slow path with lock
    with _key_manager_lock:
        if _key_manager is None:
            _key_manager = KeyManager(keys_dir)
    
    return _key_manager

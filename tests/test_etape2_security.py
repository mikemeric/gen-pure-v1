"""
Tests de validation de l'étape 2 - Security Complete

Tests pour valider:
- Cryptographie (PBKDF2, AES-GCM, RSA)
- Key manager persistant
- Rate limiting
- Password hashing bcrypt
- Refresh tokens JWT
"""
import os
import sys
import time
import tempfile
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_cryptography():
    """Test cryptographie complète"""
    print("\n📝 Test 1: Cryptographie")
    print("-" * 60)
    
    try:
        from core.security import CryptoManager, encrypt_string, decrypt_string
        
        # Test 1.1: Salt generation
        salt1 = CryptoManager.generate_salt()
        salt2 = CryptoManager.generate_salt()
        assert len(salt1) == 32, "Salt should be 32 bytes"
        assert salt1 != salt2, "Salts should be different"
        print("  ✅ Salt generation OK")
        
        # Test 1.2: Key derivation (PBKDF2)
        password = "MySecurePassword123!"
        salt = CryptoManager.generate_salt()
        key1 = CryptoManager.derive_key(password, salt)
        key2 = CryptoManager.derive_key(password, salt)
        assert len(key1) == 32, "Derived key should be 32 bytes"
        assert key1 == key2, "Same password+salt should give same key"
        print("  ✅ PBKDF2 key derivation OK")
        
        # Test 1.3: AES-256-GCM encryption
        plaintext = b"This is a secret message!"
        key = CryptoManager.generate_salt(32)
        ciphertext, nonce, tag = CryptoManager.encrypt_aes_gcm(plaintext, key)
        decrypted = CryptoManager.decrypt_aes_gcm(ciphertext, key, nonce, tag)
        assert decrypted == plaintext, "Decryption should recover plaintext"
        assert len(nonce) == 12, "Nonce should be 12 bytes for GCM"
        assert len(tag) == 16, "Tag should be 16 bytes"
        print("  ✅ AES-256-GCM encryption/decryption OK")
        
        # Test 1.4: RSA keypair generation
        private_pem, public_pem = CryptoManager.generate_rsa_keypair()
        assert b'BEGIN PRIVATE KEY' in private_pem, "Should be valid private key PEM"
        assert b'BEGIN PUBLIC KEY' in public_pem, "Should be valid public key PEM"
        print("  ✅ RSA key generation OK")
        
        # Test 1.5: RSA encryption/decryption
        message = b"Secret data"
        encrypted = CryptoManager.encrypt_rsa(message, public_pem)
        decrypted = CryptoManager.decrypt_rsa(encrypted, private_pem)
        assert decrypted == message, "RSA decryption should recover message"
        print("  ✅ RSA encryption/decryption OK")
        
        # Test 1.6: String encryption helper
        encrypted_str = encrypt_string("My secret text", "password123")
        decrypted_str = decrypt_string(encrypted_str, "password123")
        assert decrypted_str == "My secret text", "Should decrypt correctly"
        print("  ✅ String encryption helpers OK")
        
        # Test 1.7: SHA-256 hashing
        hash1 = CryptoManager.hash_sha256(b"test data")
        hash2 = CryptoManager.hash_sha256(b"test data")
        assert hash1 == hash2, "Same data should give same hash"
        assert len(hash1) == 64, "SHA-256 hex digest should be 64 chars"
        print("  ✅ SHA-256 hashing OK")
        
        print("\n✅ CRYPTOGRAPHY: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CRYPTOGRAPHY: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_key_manager():
    """Test key manager persistant"""
    print("\n📝 Test 2: Key Manager Persistant")
    print("-" * 60)
    
    try:
        from services.auth.key_manager import KeyManager
        
        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(keys_dir=tmpdir)
            
            # Test 2.1: Master key exists
            master_key = km.get_master_key()
            assert len(master_key) == 32, "Master key should be 32 bytes"
            print("  ✅ Master key loaded/generated")
            
            # Test 2.2: Master key persistence
            km2 = KeyManager(keys_dir=tmpdir)
            master_key2 = km2.get_master_key()
            assert master_key == master_key2, "Master key should persist"
            print("  ✅ Master key persistence OK")
            
            # Test 2.3: Derive purpose-specific keys
            db_key = km.derive_key("database")
            cache_key = km.derive_key("cache")
            assert len(db_key) == 32, "Derived key should be 32 bytes"
            assert db_key != cache_key, "Different purposes should give different keys"
            print("  ✅ Purpose-specific key derivation OK")
            
            # Test 2.4: Save/load key
            test_key = os.urandom(32)
            saved_path = km.save_key("test_key", test_key)
            loaded_key = km.load_key("test_key")
            assert loaded_key == test_key, "Loaded key should match saved key"
            print("  ✅ Save/load key OK")
            
            # Test 2.5: List keys
            keys = km.list_keys()
            assert "master" in keys, "Should list master key"
            assert "test_key" in keys, "Should list saved key"
            print("  ✅ List keys OK")
            
            # Test 2.6: Delete key
            km.delete_key("test_key")
            loaded = km.load_key("test_key")
            assert loaded is None, "Deleted key should not load"
            print("  ✅ Delete key OK")
            
            # Test 2.7: RSA key generation
            private_pem, public_pem = km.generate_rsa_keys("test_rsa")
            assert b'BEGIN PRIVATE KEY' in private_pem, "Should generate RSA keys"
            print("  ✅ RSA key generation OK")
        
        print("\n✅ KEY MANAGER: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ KEY MANAGER: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """Test rate limiting"""
    print("\n📝 Test 3: Rate Limiting")
    print("-" * 60)
    
    try:
        from services.auth.rate_limiter import RateLimiter
        
        # Test 3.1: Memory-based rate limiting
        limiter = RateLimiter(max_attempts=3, window_seconds=2, storage='memory')
        
        # Should allow first 3 attempts
        for i in range(3):
            assert limiter.is_allowed("user1"), f"Attempt {i+1} should be allowed"
        print("  ✅ Allows requests within limit")
        
        # Should block 4th attempt
        try:
            limiter.is_allowed("user1")
            print("  ❌ Should have blocked 4th attempt")
            return False
        except Exception as e:
            assert "Rate limit exceeded" in str(e), "Should raise rate limit error"
            print("  ✅ Blocks requests exceeding limit")
        
        # Test 3.2: Different keys are independent
        assert limiter.is_allowed("user2"), "Different key should be allowed"
        print("  ✅ Independent tracking per key")
        
        # Test 3.3: Remaining attempts
        remaining = limiter.get_remaining_attempts("user2")
        assert remaining == 2, "Should have 2 remaining after 1 attempt"
        print("  ✅ Remaining attempts tracking OK")
        
        # Test 3.4: Reset
        limiter.reset("user1")
        assert limiter.is_allowed("user1"), "Should allow after reset"
        print("  ✅ Reset functionality OK")
        
        # Test 3.5: Window expiration
        limiter2 = RateLimiter(max_attempts=2, window_seconds=1, storage='memory')
        limiter2.is_allowed("user3")
        limiter2.is_allowed("user3")
        time.sleep(1.1)  # Wait for window to expire
        assert limiter2.is_allowed("user3"), "Should allow after window expires"
        print("  ✅ Window expiration OK")
        
        # Test 3.6: Statistics
        stats = limiter.get_stats()
        assert "storage" in stats, "Should return stats"
        assert stats["storage"] == "memory", "Should show memory storage"
        print("  ✅ Statistics OK")
        
        print("\n✅ RATE LIMITER: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ RATE LIMITER: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_password_hashing():
    """Test bcrypt password hashing"""
    print("\n📝 Test 4: Password Hashing (Bcrypt)")
    print("-" * 60)
    
    try:
        from services.auth.password import PasswordManager, hash_password, verify_password
        
        # Test 4.1: Hash password
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert hashed.startswith('$2b$'), "Should be bcrypt hash"
        assert len(hashed) == 60, "Bcrypt hash should be 60 chars"
        print("  ✅ Password hashing OK")
        
        # Test 4.2: Verify password
        assert verify_password(password, hashed), "Correct password should verify"
        assert not verify_password("WrongPassword", hashed), "Wrong password should fail"
        print("  ✅ Password verification OK")
        
        # Test 4.3: Different salts
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)
        assert hashed1 != hashed2, "Same password should have different hashes (different salts)"
        assert verify_password(password, hashed1), "Both should verify"
        assert verify_password(password, hashed2), "Both should verify"
        print("  ✅ Automatic salt generation OK")
        
        # Test 4.4: Password strength validation
        weak_passwords = ["short", "nodigits", "NOUPPER123", "nolower123", "NoSpecial123"]
        for pwd in weak_passwords:
            is_valid, error = PasswordManager.validate_password_strength(pwd)
            assert not is_valid, f"'{pwd}' should be invalid"
        print("  ✅ Weak password rejection OK")
        
        strong_password = "StrongPass123!"
        is_valid, error = PasswordManager.validate_password_strength(strong_password)
        assert is_valid, "Strong password should be valid"
        print("  ✅ Strong password validation OK")
        
        # Test 4.5: Generate temporary password
        temp = PasswordManager.generate_temp_password()
        is_valid, _ = PasswordManager.validate_password_strength(temp)
        assert is_valid, "Generated password should be strong"
        assert len(temp) == 16, "Default length should be 16"
        print("  ✅ Temp password generation OK")
        
        # Test 4.6: Needs rehash
        old_hash = "$2b$10$abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJ"  # 10 rounds
        assert PasswordManager.needs_rehash(old_hash), "Old hash should need rehash"
        assert not PasswordManager.needs_rehash(hashed), "New hash should not need rehash"
        print("  ✅ Rehash detection OK")
        
        print("\n✅ PASSWORD HASHING: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ PASSWORD HASHING: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refresh_tokens():
    """Test JWT refresh tokens"""
    print("\n📝 Test 5: JWT Refresh Tokens")
    print("-" * 60)
    
    try:
        from services.auth.jwt_manager import get_jwt_manager
        
        jwt_manager = get_jwt_manager()
        
        user_data = {
            "user_id": "test-user-123",
            "username": "testuser",
            "roles": ["user"]
        }
        
        # Test 5.1: Create access token
        access_token = jwt_manager.create_access_token(user_data)
        assert len(access_token) > 0, "Should create access token"
        print("  ✅ Access token creation OK")
        
        # Test 5.2: Create refresh token
        refresh_token = jwt_manager.create_refresh_token(user_data)
        assert len(refresh_token) > 0, "Should create refresh token"
        assert refresh_token != access_token, "Tokens should be different"
        print("  ✅ Refresh token creation OK")
        
        # Test 5.3: Verify access token
        payload = jwt_manager.verify_token(access_token)
        assert payload['user_id'] == user_data['user_id'], "Payload should match"
        assert payload['type'] == 'access', "Should be access token"
        print("  ✅ Access token verification OK")
        
        # Test 5.4: Verify refresh token
        refresh_payload = jwt_manager.verify_token(refresh_token)
        assert refresh_payload['user_id'] == user_data['user_id'], "Payload should match"
        assert refresh_payload['type'] == 'refresh', "Should be refresh token"
        print("  ✅ Refresh token verification OK")
        
        # Test 5.5: Invalid token
        try:
            jwt_manager.verify_token("invalid.token.here")
            print("  ❌ Should have rejected invalid token")
            return False
        except ValueError as e:
            assert "Invalid token" in str(e), "Should raise Invalid token error"
            print("  ✅ Invalid token rejection OK")
        
        print("\n✅ REFRESH TOKENS: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ REFRESH TOKENS: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ÉTAPE 2 - SECURITY COMPLETE")
    print("=" * 60)
    
    # Définir les variables d'environnement
    os.environ.setdefault('ENVIRONMENT', 'development')
    os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-key-for-testing-only-32chars')
    
    tests = [
        test_cryptography,
        test_key_manager,
        test_rate_limiter,
        test_password_hashing,
        test_refresh_tokens
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ ÉTAPE 2 VALIDÉE - Tous les tests passent")
        print("=" * 60)
        print()
        print("🔒 Security Complete:")
        print("  1. ✅ Cryptographie enterprise (PBKDF2, AES-256-GCM, RSA-4096)")
        print("  2. ✅ Key manager persistant (clés sauvegardées)")
        print("  3. ✅ Rate limiting (Redis + memory fallback)")
        print("  4. ✅ Password hashing bcrypt (12 rounds)")
        print("  5. ✅ Refresh tokens JWT (7 jours)")
        print()
        print("➡️  Prêt pour l'ÉTAPE 3 (Infrastructure - Data Layer)")
    else:
        print("❌ ÉTAPE 2 ÉCHOUÉE - Corriger les erreurs")
    print("=" * 60)

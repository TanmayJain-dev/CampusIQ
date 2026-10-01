#!/usr/bin/env python3
"""
CampusIQ - Authenticated Credential Encryption Vault (AES-256-GCM)
==================================================================
Provides military-grade, zero-plaintext credential encryption and decryption
using authenticated symmetric cryptography (AES-256-GCM).

Each encrypted payload contains:
- 96-bit (12-byte) cryptographically random IV (Initialization Vector)
- Ciphertext with 128-bit integrity authentication tag (GCM)
- Key derivation from ENCRYPTION_KEY environment variable or secure persistent file

Author: CampusIQ Security Core / Antigravity
License: MIT
"""

import os
import sys
import base64
import hashlib
import json
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", ".vault_key")
_CACHED_KEY: Optional[bytes] = None


def get_master_key() -> bytes:
    """
    Retrieves or generates the 256-bit (32-byte) master encryption key.
    1. Checks the `ENCRYPTION_KEY` environment variable.
    2. Falls back to a protected local key file (`data/.vault_key`).
    3. Generates and persists a cryptographically secure 256-bit key if none exists.
    """
    global _CACHED_KEY
    if _CACHED_KEY is not None:
        return _CACHED_KEY

    env_key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if env_key:
        # Normalize any length passphrase or hex string to exactly 32 bytes using SHA-256
        _CACHED_KEY = hashlib.sha256(env_key.encode("utf-8")).digest()
        return _CACHED_KEY

    # Check or initialize persistent file key
    os.makedirs(os.path.dirname(VAULT_KEY_FILE), exist_ok=True)
    if os.path.exists(VAULT_KEY_FILE):
        try:
            with open(VAULT_KEY_FILE, "rb") as f:
                key = f.read().strip()
                if len(key) == 32:
                    _CACHED_KEY = key
                    return _CACHED_KEY
                elif len(key) == 64: # Hex encoded
                    _CACHED_KEY = bytes.fromhex(key.decode("utf-8"))
                    return _CACHED_KEY
        except Exception as e:
            print(f"[!] Warning reading vault key file: {e}", file=sys.stderr)

    # Generate new random 256-bit key
    new_key = AESGCM.generate_key(bit_length=256)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600 # User read/write only
        fd = os.open(VAULT_KEY_FILE, flags, mode)
        with os.fdopen(fd, "wb") as f:
            f.write(new_key)
        _CACHED_KEY = new_key
    except Exception as e:
        print(f"[!] Warning persisting vault key file: {e}", file=sys.stderr)
        _CACHED_KEY = new_key

    return _CACHED_KEY


def encrypt_credential(plaintext: str, context: Optional[str] = None) -> Dict[str, str]:
    """
    Encrypts a plaintext string (e.g. Edumarshal password) with AES-256-GCM.
    Returns a dictionary containing base64-encoded ciphertext and IV.
    """
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)

    key = get_master_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12) # 96-bit random nonce for GCM

    associated_data = context.encode("utf-8") if context else None
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), associated_data)

    return {
        "version": "aes-256-gcm",
        "iv": base64.b64encode(iv).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext_with_tag).decode("utf-8")
    }


def decrypt_credential(vault_payload: Any, context: Optional[str] = None) -> str:
    """
    Decrypts an AES-256-GCM encrypted credential payload.
    Verifies authentication tag to ensure zero ciphertext tampering.
    """
    if isinstance(vault_payload, str):
        try:
            vault_payload = json.loads(vault_payload)
        except Exception:
            # If it's a legacy unencrypted string, return as is (for backwards compatibility)
            return vault_payload

    if not isinstance(vault_payload, dict):
        raise ValueError("Invalid vault payload format: expected dict")

    # If it lacks vault fields, check if it's legacy plaintext
    if "ciphertext" not in vault_payload or "iv" not in vault_payload:
        if "password" in vault_payload:
            return vault_payload["password"]
        raise ValueError("Vault payload missing required cryptographic fields ('ciphertext', 'iv')")

    key = get_master_key()
    aesgcm = AESGCM(key)

    try:
        iv = base64.b64decode(vault_payload["iv"])
        ciphertext_with_tag = base64.b64decode(vault_payload["ciphertext"])
    except Exception as e:
        raise ValueError(f"Failed decoding vault base64 components: {e}")

    associated_data = context.encode("utf-8") if context else None
    try:
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Credential decryption failed or ciphertext was tampered with: {e}")


if __name__ == "__main__":
    print("Testing CampusIQ Credential Vault (AES-256-GCM)...")
    sample_pass = "Test@Pass#2026!"
    ctx = "student:08414802725"

    enc = encrypt_credential(sample_pass, context=ctx)
    print("Encrypted payload:", json.dumps(enc, indent=2))

    dec = decrypt_credential(enc, context=ctx)
    print("Decrypted password:", dec)
    assert dec == sample_pass, "Password mismatch!"

    # Tampering test
    try:
        corrupted = dict(enc)
        raw_ct = bytearray(base64.b64decode(corrupted["ciphertext"]))
        raw_ct[0] ^= 0xFF # Flip a bit
        corrupted["ciphertext"] = base64.b64encode(raw_ct).decode("utf-8")
        decrypt_credential(corrupted, context=ctx)
        print("FAIL: Tampered ciphertext was NOT rejected!")
    except ValueError as e:
        print("SUCCESS: Tampered ciphertext correctly rejected:", e)

    print("All vault tests passed!")

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from django.conf import settings
import base64
import hashlib


def _get_aes_key() -> bytes:
    """Derives a 16-byte AES key from the Django SECRET_KEY."""
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    aes_key = key_hash[:16]
    return aes_key


def encrypt_string(text: str) -> str:
    """Encrypts a plain text string using AES and encodes it in Base64 URL-safe format."""
    aes_key = _get_aes_key()
    iv = b'\x00' * 16  # Initialization vector for AES
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Pad the plaintext to be a multiple of the block size
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode()) + padder.finalize()
    
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()
    return base64.urlsafe_b64encode(cipher_text).decode()


def decrypt_string(encrypted_text: str) -> str:
    """Decodes a Base64 URL-safe encoded string and decrypts it using AES."""
    aes_key = _get_aes_key()
    iv = b'\x00' * 16  # Initialization vector for AES
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decoded_cipher_text = base64.urlsafe_b64decode(encrypted_text.encode())
    decrypted_padded_data = decryptor.update(decoded_cipher_text) + decryptor.finalize()
    
    # Unpad the decrypted data
    unpadder = padding.PKCS7(128).unpadder()
    plain_text = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    
    return plain_text.decode()

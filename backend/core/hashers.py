"""Verify imported hashes once; Django upgrades them to Argon2 after login."""
import hashlib
import hmac
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash

class LegacyScryptHasher(BasePasswordHasher):
    algorithm = "legacy_scrypt"

    def verify(self, password, encoded):
        try:
            _, salt, expected = encoded.split("$", 2)
            actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    def safe_summary(self, encoded):
        return {"algorithm": self.algorithm, "hash": mask_hash(encoded)}

    def must_update(self, encoded):
        return True

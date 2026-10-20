"""Password hashing for new accounts and compatibility with existing users."""

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = stored_hash.split("$")
            iterations = int(iterations)
            if not 1 <= iterations <= 1_000_000 or not salt or len(expected) != 64:
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), iterations,
            ).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, OverflowError):
            return False

    # Existing seeded/Java accounts use a plain SHA-256 digest.
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored_hash)

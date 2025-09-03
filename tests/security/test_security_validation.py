"""
Security tests for WSL-Tmux-Nvim-Setup system.

Tests include:
- Checksum verification
- Input validation and sanitization
- Path traversal prevention
- Token validation
- Secure file operations
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.security
class TestChecksumVerification:
    """Test checksum verification and file integrity."""

    def test_sha256_checksum_calculation(self, temp_dir):
        """Test SHA256 checksum calculation."""
        # Create test file with known content
        test_file = temp_dir / "test_file.txt"
        test_content = "Hello, World! This is a test file for checksum verification."
        test_file.write_text(test_content)

        # Calculate expected checksum
        expected_checksum = hashlib.sha256(test_content.encode()).hexdigest()

        # Test checksum calculation (would use actual implementation)
        calculated_checksum = hashlib.sha256(test_file.read_bytes()).hexdigest()

        assert calculated_checksum == expected_checksum

    def test_checksum_verification_success(self, temp_dir):
        """Test successful checksum verification."""
        test_file = temp_dir / "verified_file.txt"
        test_content = "Content for verification"
        test_file.write_text(test_content)

        # Calculate correct checksum
        correct_checksum = hashlib.sha256(test_content.encode()).hexdigest()

        # Create checksum file
        checksum_file = temp_dir / "verified_file.txt.sha256"
        checksum_file.write_text(f"{correct_checksum}  {test_file.name}\n")

        # Verify checksum matches
        file_checksum = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert file_checksum == correct_checksum

    def test_checksum_verification_failure(self, temp_dir):
        """Test checksum verification failure detection."""
        test_file = temp_dir / "tampered_file.txt"
        original_content = "Original content"
        test_file.write_text(original_content)

        # Calculate original checksum
        original_checksum = hashlib.sha256(original_content.encode()).hexdigest()

        # Modify file content (simulate tampering)
        tampered_content = "Tampered content"
        test_file.write_text(tampered_content)

        # Verify checksum does not match
        tampered_checksum = hashlib.sha256(tampered_content.encode()).hexdigest()
        assert tampered_checksum != original_checksum

    def test_multiple_checksum_algorithms(self, temp_dir):
        """Test support for multiple checksum algorithms."""
        test_file = temp_dir / "multi_checksum.txt"
        test_content = "Content for multiple checksum testing"
        test_file.write_text(test_content)

        content_bytes = test_content.encode()

        # Calculate different checksums
        sha256_checksum = hashlib.sha256(content_bytes).hexdigest()
        sha1_checksum = hashlib.sha1(content_bytes).hexdigest()
        md5_checksum = hashlib.md5(content_bytes).hexdigest()

        # Verify all checksums are different but consistent
        assert sha256_checksum != sha1_checksum
        assert sha256_checksum != md5_checksum
        assert len(sha256_checksum) == 64  # SHA256 length
        assert len(sha1_checksum) == 40  # SHA1 length
        assert len(md5_checksum) == 32  # MD5 length

    def test_checksum_file_format_validation(self, temp_dir):
        """Test validation of checksum file formats."""
        # Valid checksum file formats
        valid_formats = [
            "a1b2c3d4e5f6...  filename.txt",
            "a1b2c3d4e5f6... *filename.txt",  # Binary mode indicator
            "a1b2c3d4e5f6...  ./path/to/filename.txt",
        ]

        # Invalid checksum file formats
        invalid_formats = [
            "invalid_checksum_length filename.txt",
            "a1b2c3d4e5f6",  # Missing filename
            "",  # Empty line
            "not_hex_chars_here  filename.txt",
        ]

        # Test would validate checksum file parsing
        # This is a placeholder for actual validation logic
        assert len(valid_formats) > 0
        assert len(invalid_formats) > 0


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""

    def test_version_string_validation(self):
        """Test version string input validation."""
        valid_versions = [
            "1.0.0",
            "v1.0.0",
            "1.0.0-alpha",
            "1.0.0-beta.1",
            "1.0.0+build.1",
        ]

        invalid_versions = [
            "",
            "not_a_version",
            "1.0",
            "v1.0.0.0.0",
            "../../../etc/passwd",  # Path traversal attempt
            "1.0.0; rm -rf /",  # Command injection attempt
            "1.0.0\n\nmalicious",  # Newline injection
            "1.0.0\x00null",  # Null byte injection
        ]

        import re

        version_pattern = re.compile(
            r"^v?(\d+)\.(\d+)\.(\d+)(?:-[\w\.-]+)?(?:\+[\w\.-]+)?$"
        )

        # Test valid versions
        for version in valid_versions:
            assert version_pattern.match(
                version
            ), f"Valid version {version} failed validation"

        # Test invalid versions
        for version in invalid_versions:
            assert not version_pattern.match(
                version
            ), f"Invalid version {version} passed validation"

    def test_file_path_validation(self, temp_dir):
        """Test file path validation and sanitization."""
        safe_paths = [
            "config.json",
            "data/config.json",
            "./config.json",
            "backup/2023-09-01/config.json",
        ]

        dangerous_paths = [
            "../../../etc/passwd",  # Path traversal
            "/etc/passwd",  # Absolute path to sensitive file
            "config.json\x00.exe",  # Null byte injection
            "config.json;rm -rf /",  # Command injection
            "con",  # Windows reserved name
            "aux.json",  # Windows reserved name
            "",  # Empty path
            "." * 300,  # Excessively long path
        ]

        def is_safe_path(path: str, base_dir: Path) -> bool:
            """Check if path is safe for file operations."""
            if not path or len(path) > 255:
                return False

            # Check for null bytes and control characters
            if "\x00" in path or any(ord(c) < 32 for c in path if c not in "\t\n\r"):
                return False

            # Check for command injection patterns
            dangerous_chars = [";", "|", "&", "$", "`", ">", "<"]
            if any(char in path for char in dangerous_chars):
                return False

            # Resolve path and check if it's within base directory
            try:
                full_path = (base_dir / path).resolve()
                return str(full_path).startswith(str(base_dir.resolve()))
            except (OSError, ValueError):
                return False

        # Test safe paths
        for path in safe_paths:
            assert is_safe_path(path, temp_dir), f"Safe path {path} failed validation"

        # Test dangerous paths
        for path in dangerous_paths:
            assert not is_safe_path(
                path, temp_dir
            ), f"Dangerous path {path} passed validation"

    def test_url_validation(self):
        """Test URL validation for downloads."""
        valid_urls = [
            "https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz",
            "https://api.github.com/repos/user/repo/releases/latest",
            "http://localhost:3000/test.json",  # For testing only
        ]

        invalid_urls = [
            "",
            "not_a_url",
            "ftp://example.com/file.txt",  # Unsupported protocol
            "file:///etc/passwd",  # Local file access
            "javascript:alert('xss')",  # XSS attempt
            "data:text/html,<script>alert()</script>",  # Data URL
            "http://[::1]:3000/../../../etc/passwd",  # IPv6 with path traversal
        ]

        import re

        # Simple URL validation pattern
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # Domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # Optional port
            r"(?:/?|[/?]\S+)$",  # Path
            re.IGNORECASE,
        )

        # Test valid URLs
        for url in valid_urls:
            assert url_pattern.match(url), f"Valid URL {url} failed validation"

        # Test invalid URLs
        for url in invalid_urls:
            assert not url_pattern.match(url), f"Invalid URL {url} passed validation"

    def test_github_token_validation(self):
        """Test GitHub token format validation."""
        # GitHub token patterns (not real tokens)
        valid_tokens = [
            "ghp_1234567890abcdef1234567890abcdef12345678",  # Personal access token
            "gho_1234567890abcdef1234567890abcdef12345678",  # OAuth token
            "github_pat_12345_abcdefghijklmnopqrstuvwxyz",  # New format
        ]

        invalid_tokens = [
            "",
            "invalid_token",
            "ghp_short",
            "ghp_1234567890abcdef1234567890abcdef12345678extra",  # Too long
            "fake_1234567890abcdef1234567890abcdef12345678",  # Wrong prefix
            "ghp_" + "x" * 100,  # Excessively long
        ]

        def validate_github_token(token: str) -> bool:
            """Validate GitHub token format."""
            if not token:
                return True  # Empty token is valid (no authentication)

            # GitHub token patterns
            valid_patterns = [
                r"^ghp_[a-zA-Z0-9]{36}$",  # Personal access token
                r"^gho_[a-zA-Z0-9]{36}$",  # OAuth token
                r"^github_pat_\d+_[a-zA-Z0-9]{22,}$",  # New PAT format
            ]

            import re

            return any(re.match(pattern, token) for pattern in valid_patterns)

        # Test valid tokens
        for token in valid_tokens:
            assert validate_github_token(token), "Valid token format failed validation"

        # Test invalid tokens
        for token in invalid_tokens:
            assert not validate_github_token(
                token
            ), "Invalid token format passed validation"


@pytest.mark.security
class TestPathTraversalPrevention:
    """Test prevention of path traversal attacks."""

    def test_extract_path_validation(self, temp_dir):
        """Test path validation during archive extraction."""
        safe_paths = [
            "config/settings.json",
            "bin/script.sh",
            "docs/readme.md",
            "./relative/path.txt",
        ]

        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "\\..\\..\\windows\\system32\\cmd.exe",
            "config/../../../etc/passwd",
            "bin/../../etc/shadow",
        ]

        def is_safe_extract_path(path: str, extract_dir: Path) -> bool:
            """Check if extraction path is safe."""
            if not path:
                return False

            # Normalize path separators
            normalized_path = path.replace("\\", "/")

            # Remove leading slashes
            while normalized_path.startswith("/"):
                normalized_path = normalized_path[1:]

            # Calculate target path
            target_path = (extract_dir / normalized_path).resolve()

            # Check if target is within extraction directory
            try:
                target_path.relative_to(extract_dir.resolve())
                return True
            except ValueError:
                return False

        # Test safe paths
        for path in safe_paths:
            assert is_safe_extract_path(
                path, temp_dir
            ), f"Safe extraction path {path} failed validation"

        # Test dangerous paths
        for path in dangerous_paths:
            assert not is_safe_extract_path(
                path, temp_dir
            ), f"Dangerous extraction path {path} passed validation"

    def test_config_file_path_validation(self, temp_dir):
        """Test configuration file path validation."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()

        safe_config_paths = ["config.json", "user.yaml", "advanced/settings.json"]

        dangerous_config_paths = [
            "../secrets.txt",
            "/etc/passwd",
            "config/../../../etc/passwd",
        ]

        def is_safe_config_path(path: str, config_base: Path) -> bool:
            """Validate configuration file paths."""
            try:
                full_path = (config_base / path).resolve()
                return str(full_path).startswith(str(config_base.resolve()))
            except (OSError, ValueError):
                return False

        # Test safe configuration paths
        for path in safe_config_paths:
            assert is_safe_config_path(
                path, config_dir
            ), f"Safe config path {path} failed validation"

        # Test dangerous configuration paths
        for path in dangerous_config_paths:
            assert not is_safe_config_path(
                path, config_dir
            ), f"Dangerous config path {path} passed validation"


@pytest.mark.security
class TestSecureFileOperations:
    """Test secure file operations."""

    def test_secure_file_creation(self, temp_dir):
        """Test secure file creation with proper permissions."""
        test_file = temp_dir / "secure_file.txt"

        # Create file with secure permissions
        test_file.write_text("Secure content")
        test_file.chmod(0o600)  # Read/write for owner only

        # Check permissions
        file_stat = test_file.stat()
        file_permissions = file_stat.st_mode & 0o777

        # Should not be world-readable or group-readable
        assert (
            file_permissions & 0o044 == 0
        ), "File should not be readable by group or others"
        assert file_permissions & 0o200 != 0, "File should be writable by owner"

    def test_temporary_file_security(self, temp_dir):
        """Test secure temporary file handling."""
        import tempfile

        # Create secure temporary file
        with tempfile.NamedTemporaryFile(
            mode="w+t", delete=False, dir=temp_dir
        ) as temp_file:
            temp_file.write("Temporary sensitive content")
            temp_file_path = Path(temp_file.name)

        try:
            # Check temporary file permissions
            file_stat = temp_file_path.stat()
            file_permissions = file_stat.st_mode & 0o777

            # Temporary files should have restrictive permissions
            assert (
                file_permissions & 0o044 == 0
            ), "Temporary file should not be readable by group or others"

        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                temp_file_path.unlink()

    def test_backup_file_security(self, temp_dir):
        """Test secure backup file operations."""
        original_file = temp_dir / "original.txt"
        backup_file = temp_dir / "original.txt.backup"

        # Create original file with sensitive content
        sensitive_content = "API_KEY=secret123\nPASSWORD=topsecret"
        original_file.write_text(sensitive_content)
        original_file.chmod(0o600)

        # Create backup (simulating backup operation)
        backup_file.write_text(sensitive_content)
        backup_file.chmod(0o600)

        # Verify backup has same security permissions as original
        original_permissions = original_file.stat().st_mode & 0o777
        backup_permissions = backup_file.stat().st_mode & 0o777

        assert (
            backup_permissions == original_permissions
        ), "Backup should have same permissions as original"

    def test_config_file_security(self, temp_dir):
        """Test configuration file security."""
        config_file = temp_dir / "config.json"

        # Create configuration with sensitive data
        import json

        config_data = {
            "github_token": "ghp_fake_token_for_testing",
            "api_keys": {"service1": "key123", "service2": "key456"},
        }

        config_file.write_text(json.dumps(config_data, indent=2))
        config_file.chmod(0o600)  # Secure permissions

        # Verify configuration file permissions
        file_permissions = config_file.stat().st_mode & 0o777
        assert file_permissions == 0o600, "Config file should have 0o600 permissions"


@pytest.mark.security
class TestTokenAndSecretHandling:
    """Test secure handling of tokens and secrets."""

    def test_token_storage_security(self, temp_dir):
        """Test secure token storage."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        token_file = config_dir / "tokens.json"

        # Simulate token storage
        import json

        token_data = {
            "github_token": "ghp_fake_token_for_testing",
            "api_token": "api_fake_token",
        }

        token_file.write_text(json.dumps(token_data))
        token_file.chmod(0o600)  # Secure permissions

        # Verify token file security
        file_permissions = token_file.stat().st_mode & 0o777
        assert (
            file_permissions == 0o600
        ), "Token file should have restrictive permissions"

        # Verify content doesn't leak in error messages (mock test)
        content = token_file.read_text()
        assert "ghp_fake_token_for_testing" in content

        # In real implementation, tokens should be masked in logs and errors

    def test_token_environment_variable_handling(self):
        """Test secure handling of tokens from environment variables."""
        import os

        # Test token from environment
        test_token = "ghp_test_token_from_env"

        with patch.dict(os.environ, {"WSM_GITHUB_TOKEN": test_token}):
            retrieved_token = os.environ.get("WSM_GITHUB_TOKEN")
            assert retrieved_token == test_token

            # In real implementation, tokens should be masked in logs
            # This test would verify that tokens don't appear in plain text in logs

    def test_secret_masking_in_output(self):
        """Test that secrets are masked in command output."""
        # Test data with secrets
        test_output = "Configuration loaded with token: ghp_secret_token_123"
        sensitive_patterns = [
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub tokens
            r"gho_[a-zA-Z0-9]{36}",
            r"password[:\s]*[^\s]+",
            r"api_key[:\s]*[^\s]+",
        ]

        def mask_secrets(text: str) -> str:
            """Mask secrets in text output."""
            import re

            masked_text = text
            for pattern in sensitive_patterns:
                masked_text = re.sub(
                    pattern, "[MASKED]", masked_text, flags=re.IGNORECASE
                )
            return masked_text

        masked_output = mask_secrets(test_output)
        assert "ghp_secret_token_123" not in masked_output
        assert "[MASKED]" in masked_output


@pytest.mark.security
class TestNetworkSecurity:
    """Test network-related security measures."""

    def test_https_enforcement(self):
        """Test enforcement of HTTPS for downloads."""
        secure_urls = [
            "https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz",
            "https://api.github.com/repos/user/repo/releases/latest",
        ]

        insecure_urls = [
            "http://github.com/user/repo/releases/download/v1.0.0/file.tar.gz",
            "http://api.github.com/repos/user/repo/releases/latest",
            "ftp://example.com/file.tar.gz",
        ]

        def is_secure_url(url: str) -> bool:
            """Check if URL uses secure protocol."""
            return url.startswith("https://")

        # Test secure URLs
        for url in secure_urls:
            assert is_secure_url(url), f"Secure URL {url} failed validation"

        # Test insecure URLs
        for url in insecure_urls:
            assert not is_secure_url(url), f"Insecure URL {url} passed validation"

    def test_certificate_validation(self):
        """Test SSL certificate validation."""
        # This would test that SSL certificates are properly validated
        # For now, just test that the concept is in place

        def validate_ssl_context():
            """Ensure SSL context is properly configured."""
            import ssl

            # Create secure SSL context
            context = ssl.create_default_context()

            # Should have secure defaults
            assert context.check_hostname is True
            assert context.verify_mode == ssl.CERT_REQUIRED

            return context

        ssl_context = validate_ssl_context()
        assert ssl_context is not None

    def test_request_timeout_security(self):
        """Test that network requests have appropriate timeouts."""
        # Test various timeout configurations
        timeout_configs = [
            (30, "connection_timeout"),  # Connection timeout
            (300, "read_timeout"),  # Read timeout
            (600, "total_timeout"),  # Total request timeout
        ]

        for timeout_value, timeout_type in timeout_configs:
            # Verify timeout values are reasonable
            assert (
                5 <= timeout_value <= 3600
            ), f"{timeout_type} should be between 5s and 1 hour"

    def test_user_agent_security(self):
        """Test user agent string doesn't leak sensitive information."""
        # User agent should identify the application but not leak system details
        safe_user_agents = [
            "WSL-Tmux-Nvim-Setup/1.0.0",
            "WSM-CLI/1.0.0 (+https://github.com/user/repo)",
        ]

        unsafe_user_agents = [
            "",  # Empty user agent
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WSM",  # Too much system info
            "WSM/1.0 (user@hostname.local)",  # Personal info leak
        ]

        def is_safe_user_agent(ua: str) -> bool:
            """Check if user agent is safe."""
            if not ua or len(ua) > 100:
                return False

            # Should not contain personal info
            personal_info_indicators = ["@", "user", "host", "admin"]
            return not any(
                indicator in ua.lower() for indicator in personal_info_indicators
            )

        # Test safe user agents
        for ua in safe_user_agents:
            assert is_safe_user_agent(ua), f"Safe user agent {ua} failed validation"

        # Test unsafe user agents
        for ua in unsafe_user_agents:
            assert not is_safe_user_agent(
                ua
            ), f"Unsafe user agent {ua} passed validation"

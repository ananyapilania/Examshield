"""
Unit tests for SHA-256 Paper Hashing Module (backend/hashing.py).
Tests:
1. Same file → same hash
2. Different files → different hash
3. Modified file → different hash
4. Missing file handling
5. verify_paper_hash helper behavior
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from backend.hashing import calculate_sha256, verify_paper_hash


class TestHashing(unittest.TestCase):
    """Test suite for SHA-256 cryptographic paper fingerprinting."""

    def setUp(self):
        """Create a temporary directory for synthetic test documents."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    def _create_file(self, filename: str, content: bytes) -> Path:
        """Helper to create a synthetic binary file."""
        file_path = self.dir_path / filename
        file_path.write_bytes(content)
        return file_path

    def test_same_file_same_hash(self):
        """1. Same file content produces identical SHA-256 hash."""
        content = b"ExamShield Synthetic Examination Paper Data - CS101 Set A"
        file1 = self._create_file("paper1.bin", content)
        file2 = self._create_file("paper2.bin", content)

        hash1 = calculate_sha256(file1)
        hash2 = calculate_sha256(file2)

        # Hash must match expected standard hashlib calculation
        expected_hash = hashlib.sha256(content).hexdigest()

        self.assertEqual(hash1, hash2)
        self.assertEqual(hash1, expected_hash)
        self.assertEqual(len(hash1), 64)

    def test_different_files_different_hash(self):
        """2. Different files produce different SHA-256 hashes."""
        file_a = self._create_file("math_exam.bin", b"Mathematics Paper Version 1")
        file_b = self._create_file("physics_exam.bin", b"Physics Paper Version 1")

        hash_a = calculate_sha256(file_a)
        hash_b = calculate_sha256(file_b)

        self.assertNotEqual(hash_a, hash_b)

    def test_modified_file_different_hash(self):
        """3. Modifying even 1 byte/character alters the SHA-256 hash (Avalanche effect)."""
        original_content = b"Question 1: What is 2 + 2? Option A: 4, Option B: 5"
        modified_content = b"Question 1: What is 2 + 2? Option A: 4, Option B: 6"  # Tampered option

        original_file = self._create_file("original.bin", original_content)
        tampered_file = self._create_file("tampered.bin", modified_content)

        original_hash = calculate_sha256(original_file)
        tampered_hash = calculate_sha256(tampered_file)

        self.assertNotEqual(original_hash, tampered_hash)

    def test_missing_file_handling(self):
        """4. Attempting to hash a missing file raises FileNotFoundError."""
        non_existent_path = self.dir_path / "non_existent_paper.bin"
        with self.assertRaises(FileNotFoundError):
            calculate_sha256(non_existent_path)

    def test_directory_path_handling(self):
        """Passing a directory instead of a file raises IsADirectoryError."""
        with self.assertRaises(IsADirectoryError):
            calculate_sha256(self.dir_path)

    def test_verify_paper_hash(self):
        """Test verify_paper_hash returns True on match and False on mismatch."""
        content = b"ExamShield Verification Test Content"
        file_path = self._create_file("verify_test.bin", content)
        correct_hash = hashlib.sha256(content).hexdigest()
        incorrect_hash = "0" * 64

        self.assertTrue(verify_paper_hash(file_path, correct_hash))
        self.assertTrue(verify_paper_hash(file_path, correct_hash.upper()))  # Case-insensitive
        self.assertFalse(verify_paper_hash(file_path, incorrect_hash))


if __name__ == "__main__":
    unittest.main()

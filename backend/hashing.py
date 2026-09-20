"""
ExamShield - SHA-256 Hashing Engine (Security Core)
Part 1 Prototype: Cryptographic paper fingerprinting.

Concept:
    PDF / File
        ↓
    Binary chunk reading
        ↓
    SHA-256 digest computation
        ↓
    64-character hexadecimal digital fingerprint

SHA-256 serves as the immutable digital fingerprint of the examination paper.
Due to the avalanche effect in cryptographic hashing, even a single-bit alteration
in the file will completely alter the output hash, enabling robust tamper detection.
"""

import hashlib
import os
from pathlib import Path
from typing import Union


def calculate_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """
    Calculate the SHA-256 cryptographic hash of a given file.

    Reads the file in binary chunks to handle large documents efficiently
    without consuming excessive memory.

    Args:
        file_path (Union[str, Path]): Path to the examination paper file.
        chunk_size (int, optional): Size of bytes to read per iteration (default: 64 KB).

    Returns:
        str: 64-character lowercase hexadecimal SHA-256 digest.

    Raises:
        FileNotFoundError: If the file does not exist at the specified path.
        IsADirectoryError: If the path points to a directory instead of a file.
        PermissionError: If the application lacks read permissions.
    """
    path_obj = Path(file_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Examination file not found: {file_path}")

    if not path_obj.is_file():
        raise IsADirectoryError(f"Specified path is not a file: {file_path}")

    sha256_hash = hashlib.sha256()

    # Read the file in binary mode chunk-by-chunk
    with open(path_obj, "rb") as file_stream:
        while chunk := file_stream.read(chunk_size):
            sha256_hash.update(chunk)

    # Return the 64-character hexadecimal digest (the digital fingerprint)
    return sha256_hash.hexdigest()


def verify_paper_hash(file_path: Union[str, Path], expected_hash: str) -> bool:
    """
    Verify if a paper's calculated SHA-256 hash matches the expected baseline hash.

    Args:
        file_path (Union[str, Path]): Path to the candidate paper file.
        expected_hash (str): The baseline 64-character SHA-256 hash.

    Returns:
        bool: True if hashes match exactly (authentic), False if mismatched (tampered).
    """
    calculated_hash = calculate_sha256(file_path)
    return calculated_hash.strip().lower() == expected_hash.strip().lower()

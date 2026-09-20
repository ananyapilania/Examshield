"""
Unit tests for Backup Question Bank (backup_questions/questions.json).
Corresponds to TC-06 in docs/test_cases.md:
- TC-06: Backup Question Bank Loading & Schema Validation
"""

import json
from pathlib import Path
import pytest


def get_questions_file_path() -> Path:
    """Resolve the path to backup_questions/questions.json."""
    # From tests/ directory, root is parent directory
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "backup_questions" / "questions.json"


def test_question_bank_file_exists():
    """Verify that backup_questions/questions.json exists."""
    file_path = get_questions_file_path()
    assert file_path.exists(), f"Question bank file not found at {file_path}"
    assert file_path.is_file(), f"Question bank path {file_path} is not a file"


def test_question_bank_valid_json_structure():
    """Verify that questions.json parses into a non-empty list."""
    file_path = get_questions_file_path()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list), "Root element of questions.json must be a JSON array (list)"
    assert len(data) > 0, "Question bank must contain at least one question"


def test_question_items_schema_conformance():
    """
    Verify TC-06 requirement:
    Each question item contains required fields (id, subject, topic, difficulty, marks, question, options, correct_answer, status).
    """
    file_path = get_questions_file_path()
    with open(file_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    required_fields = {
        "id", "subject", "topic", "difficulty", "marks",
        "question", "options", "correct_answer", "status"
    }
    allowed_difficulties = {"Easy", "Medium", "Hard"}
    seen_ids = set()

    for idx, item in enumerate(questions):
        assert isinstance(item, dict), f"Question at index {idx} must be a JSON object (dict)"

        # 1. Check all required fields are present
        missing = required_fields - set(item.keys())
        assert not missing, f"Question at index {idx} ({item.get('id')}) is missing required fields: {missing}"

        # 2. Check field types and non-empty values
        assert isinstance(item["id"], str) and item["id"].strip(), f"Invalid 'id' at index {idx}"
        assert item["id"] not in seen_ids, f"Duplicate question id '{item['id']}' found at index {idx}"
        seen_ids.add(item["id"])

        assert isinstance(item["subject"], str) and item["subject"].strip(), f"Invalid 'subject' for {item['id']}"
        assert isinstance(item["topic"], str) and item["topic"].strip(), f"Invalid 'topic' for {item['id']}"
        assert item["difficulty"] in allowed_difficulties, f"Invalid 'difficulty' '{item['difficulty']}' for {item['id']}"

        assert isinstance(item["marks"], int) and item["marks"] > 0, f"Marks must be a positive integer for {item['id']}"
        assert isinstance(item["question"], str) and item["question"].strip(), f"Invalid 'question' text for {item['id']}"

        # 3. Check options and correct answer
        assert isinstance(item["options"], list) and len(item["options"]) >= 2, f"Options must be a list of at least 2 items for {item['id']}"
        for opt in item["options"]:
            assert isinstance(opt, str) and opt.strip(), f"Option text must be a non-empty string in {item['id']}"

        assert isinstance(item["correct_answer"], str) and item["correct_answer"].strip(), f"Invalid 'correct_answer' for {item['id']}"
        assert item["correct_answer"] in item["options"], f"Correct answer must be one of the options for {item['id']}"

        assert isinstance(item["status"], str) and item["status"].strip(), f"Invalid 'status' for {item['id']}"

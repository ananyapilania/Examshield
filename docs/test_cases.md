# ExamShield — Test Cases & Validation Plan (Part 1)

## 1. Test Overview
This document outlines test specifications for verifying the Part 1 security prototype of ExamShield.

---

## 2. Test Cases Matrix

| Test ID | Test Scenario | Preconditions | Input / Action | Expected Result | Pass / Fail Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | **SHA-256 Hash Generation** | Clean test file created | Compute SHA-256 hash on a sample paper file | Deterministic 64-character hex hash returned; matches reference hash | Hash string length is exactly 64 and matches expected cryptographic digest |
| **TC-02** | **Exam Paper Metadata Registration** | SQLite DB initialized | Register paper with Exam ID `EXAM-TEST-001`, title, and calculated hash | Record inserted successfully into `exam_papers` table with UTC timestamp | Record queryable by `exam_id` with exact matching hash |
| **TC-03** | **Authentic Paper Verification** | Paper registered in DB | Verify unaltered original paper against `EXAM-TEST-001` | Status returned: `AUTHENTIC` / Match verified | Calculated hash equals stored hash; success audit log emitted |
| **TC-04** | **Tamper Detection (Single Bit / Byte Alteration)** | Paper registered in DB | Verify modified/leaked paper against `EXAM-TEST-001` | Status returned: `TAMPERED` / Mismatch detected | Calculated hash differs from stored hash; alert audit log emitted |
| **TC-05** | **Audit Log Emission** | SQLite DB initialized | Execute upload and verification operations | Entries created in `audit_logs` with timestamps, event types, and Exam IDs | All lifecycle actions recorded sequentially in SQLite audit table |
| **TC-06** | **Backup Question Bank Loading** | `questions.json` present | Load and parse `backup_questions/questions.json` | Valid JSON array loaded; question items contain required fields (`id`, `subject`, `difficulty`, `marks`) | Parsing succeeds with 100% schema conformance |
| **TC-07** | **Security / Git Ignored Assets Check** | Local repo clone | Check `git status` after generating PDF/DB files | PDFs, SQLite `.db` files, and paper directories remain untracked | No sensitive files appear in Git staging |

---

## 3. Execution Methodology

1. **Automated Unit Tests**: Standard unit tests using Python's `unittest` or `pytest`.
2. **Tamper Simulation Tests**: Synthetic mutation of sample papers to ensure 100% tamper detection accuracy.
3. **Audit Log Verification**: Querying the database to confirm chronological entry ordering.

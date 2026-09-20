# ExamShield — Functional & Non-Functional Requirements (Part 1)

## 1. Project Overview
ExamShield is an examination paper security and leak prevention system. This document specifies the requirements for **Part 1** (~20% milestone for Review II).

---

## 2. Part 1 Scope & Core Capabilities

Part 1 focuses on establishing the baseline security prototype for paper integrity, hashing, metadata storage, verification, and audit logging.

### 2.1 Functional Requirements

1. **Exam Paper Upload**:
   - The system must accept examination paper uploads.
   - The system must validate upload constraints (file format, non-empty files).
   - Uploaded files must be securely handled and stored in local working paths (never tracked in version control).

2. **Exam ID Generation & Assignment**:
   - Every registered exam paper must be assigned a unique Exam ID.
   - The Exam ID serves as the primary identifier correlating metadata, cryptographic fingerprints, and audit logs.

3. **Cryptographic Hashing (SHA-256)**:
   - The system must compute a deterministic SHA-256 cryptographic hash of the original examination paper upon upload.
   - The hash value serves as the immutable digital fingerprint for integrity verification.

4. **Metadata Storage (SQLite)**:
   - An SQLite database must store paper metadata, including:
     - `exam_id` (Primary Key)
     - `title` / `subject`
     - `file_name`
     - `sha256_hash`
     - `upload_timestamp`
     - `status` (e.g., `REGISTERED`, `VERIFIED`, `FLAGGED`)
   - Database operations must ensure relational integrity and fast lookup.

5. **Paper Verification & Integrity Check**:
   - The system must provide a verification module to compare the hash of a target/submitted paper against the registered hash stored in the SQLite database.
   - The verification output must clearly indicate a match (`AUTHENTIC`) or mismatch (`TAMPERED`).

6. **Tamper Detection Simulation**:
   - The system must detect unauthorized modifications or leaked variants by comparing incoming file hashes with the baseline original hash.
   - Immediate security alerts/flags must be triggered upon detecting any discrepancy.

7. **Audit Logging**:
   - The system must maintain an append-only audit trail logging:
     - Event type (`UPLOAD`, `VERIFY`, `TAMPER_DETECTED`, `QUERY`)
     - Associated Exam ID
     - Timestamp (ISO 8601 UTC)
     - Result status & descriptive event message.

8. **Backup Question Bank Foundation**:
   - The system must include a structured JSON question bank foundation (`backup_questions/questions.json`) to serve as the data source for backup question sets and fallback workflows.

---

### 2.2 Security & Operational Constraints

- **Repository Cleanliness**: Real examination papers and PDF documents must NEVER be committed to Git.
- **Environment Isolation**: Python virtual environments (`venv/`), temporary runtime files, and SQLite database files (`*.db`) must be excluded via `.gitignore`.
- **Scope Boundary**: Advanced modules (Blockchain, OCR, embeddings, watermarking, GNN, ZKP, RAG, differential privacy, automatic replacement) are scheduled for subsequent project phases (Parts 2 and 3) and are explicitly out of scope for Part 1.

---

## 3. Non-Functional Requirements

| Metric | Requirement |
| :--- | :--- |
| **Integrity Standard** | NIST SHA-256 cryptographic digest |
| **Response Time** | Hash generation and database verification < 100ms for standard papers |
| **Storage Engine** | SQLite 3 with WAL mode support |
| **Portability** | Cross-platform compatibility (macOS / Linux / Windows) |
| **Audit Compliance** | Append-only logging with chronological timestamps |

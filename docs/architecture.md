# ExamShield — System Architecture (Part 1 Prototype)

## 1. Architectural Overview

ExamShield Part 1 is structured as a modular, lightweight security prototype focused on cryptographic validation, metadata persistence, tamper detection, and audit logging.

```
┌────────────────────────────────────────────────────────┐
│                   ExamShield Client                    │
│            (CLI / Minimal API Interface)               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Backend Services                     │
│  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │   Paper Ingestion     │  │  Hash Engine (SHA256) │  │
│  │   & Exam ID Generator │  │  Digest & Integrity   │  │
│  └───────────┬───────────┘  └───────────┬───────────┘  │
│              │                          │              │
│              ▼                          ▼              │
│  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │ Verification Service  │  │  Audit Logger Engine  │  │
│  │ & Tamper Detection    │  │  (Timestamped Events) │  │
│  └───────────────────────┘  └───────────────────────┘  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Storage Layer                        │
│  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │   SQLite Database     │  │ Backup Question Bank  │  │
│  │ (Papers & Audit Logs) │  │   (questions.json)    │  │
│  └───────────────────────┘  └───────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules (Part 1)

### 2.1 Paper Ingestion & Exam ID Generator
- Accepts exam paper input.
- Assigns a unique, deterministic or UUID-based `Exam ID`.
- Reads binary streams chunk by chunk to prevent memory spikes.

### 2.2 SHA-256 Hashing Engine
- Computes SHA-256 digest over the binary stream:
  $$\text{Hash} = \text{SHA-256}(\text{Paper Bytes})$$
- Generates a 64-character hexadecimal digest representing the unalterable fingerprint of the paper.

### 2.3 Verification & Tamper Detection Engine
- Takes an incoming paper file and target `Exam ID`.
- Computes the candidate file's SHA-256 hash.
- Fetches the baseline hash stored in SQLite.
- Status determination:
  - **MATCH**: Integrity verified (`AUTHENTIC`).
  - **MISMATCH**: Paper altered or leaked version detected (`TAMPERED`).

### 2.4 Audit Logging Module
- Records all actions systematically to provide an immutable forensic log.
- Every check, upload, and discrepancy is logged with exact timestamps.

### 2.5 Backup Question Bank
- Provides fallback question repository formatted in JSON.
- Categorized by subject, difficulty, marks, and unique question ID.

---

## 3. Database Schema (SQLite)

### Table: `exams`
Stores metadata and cryptographic hashes for registered examination papers.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `exam_id` | TEXT | PRIMARY KEY | Unique Examination Identifier (e.g., `EXAM-2026-CS101`) |
| `exam_name` | TEXT | NOT NULL | Title / Display Name of the Examination |
| `subject` | TEXT | NOT NULL | Subject / Course Name |
| `academic_year` | TEXT | NOT NULL | Academic Session / Year (e.g., `2025-2026`) |
| `paper_version` | TEXT | NOT NULL | Version / Set Identifier (e.g., `Set-A`, `v1.0`) |
| `file_hash` | TEXT | NOT NULL | 64-character lowercase hexadecimal SHA-256 fingerprint |
| `created_at` | TEXT | NOT NULL | Registration ISO 8601 UTC timestamp |
| `status` | TEXT | NOT NULL | `REGISTERED`, `VERIFIED`, `FLAGGED`, `TAMPER_DETECTED` |

### Table: `audit_logs`
Chronological event logging for operations and security checks.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique audit log entry ID |
| `exam_id` | TEXT | NOT NULL | Associated Exam ID |
| `action` | TEXT | NOT NULL | `PAPER_REGISTERED`, `PAPER_VERIFIED`, `HASH_MISMATCH`, `STATUS_UPDATED` |
| `timestamp` | TEXT | NOT NULL | ISO 8601 UTC event timestamp |
| `result` | TEXT | NOT NULL | `SUCCESS`, `FAILURE`, `FLAGGED` |
| `details` | TEXT | NULLABLE | Descriptive event details & outcome |

---

## 4. Security Boundaries

- **No PDF / Real Paper Storage in Git**:
  - `papers/original/` and `papers/leaked/` are git-ignored.
  - Only `.gitkeep` markers are checked into Git.
- **Local SQLite Storage**:
  - Database files are stored locally during execution and excluded from source control.

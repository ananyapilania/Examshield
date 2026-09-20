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

### Table: `exam_papers`
Stores metadata and cryptographic hashes for registered examination papers.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `exam_id` | TEXT | PRIMARY KEY | Unique Examination Identifier (e.g., `EXAM-2026-CS101`) |
| `title` | TEXT | NOT NULL | Title / Subject Name |
| `file_name` | TEXT | NOT NULL | Name of uploaded document |
| `sha256_hash` | TEXT | NOT NULL | 64-character SHA-256 hex string |
| `created_at` | DATETIME | NOT NULL | Registration timestamp (UTC) |
| `status` | TEXT | NOT NULL | `REGISTERED`, `VERIFIED`, `FLAGGED` |

### Table: `audit_logs`
Chronological event logging for operations and security checks.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique log entry ID |
| `exam_id` | TEXT | REFERENCES `exam_papers(exam_id)` | Associated Exam ID |
| `event_type` | TEXT | NOT NULL | `UPLOAD`, `VERIFY_SUCCESS`, `TAMPER_DETECTED` |
| `details` | TEXT | NOT NULL | Descriptive event details & outcome |
| `timestamp` | DATETIME | NOT NULL | Event timestamp (UTC) |

---

## 4. Security Boundaries

- **No PDF / Real Paper Storage in Git**:
  - `papers/original/` and `papers/leaked/` are git-ignored.
  - Only `.gitkeep` markers are checked into Git.
- **Local SQLite Storage**:
  - Database files are stored locally during execution and excluded from source control.

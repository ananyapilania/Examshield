# ExamShield 🛡️
> **Examination Paper Security & Integrity System**  
> *Part 1: Security Prototype (~20% Completion Milestone for Review II)*

---

## 📌 Project Overview
**ExamShield** is designed to prevent examination paper leaks, ensure unalterable document integrity, and provide forensic traceability during high-stakes assessments.

This repository hosts **Part 1** of a 3-part development roadmap, representing approximately 20% completion for **Review II**.

---

## 🎯 Part 1 Scope & Core Capabilities
1. **Exam Paper Upload**: Ingestion interface for examination papers.
2. **Exam ID Assignment**: Unique identifier generation indexing paper metadata.
3. **SHA-256 Cryptographic Hashing**: Deterministic digest generation for tamper-proof fingerprinting.
4. **SQLite Metadata Storage**: Lightweight, reliable local persistence for paper metadata and records.
5. **Paper Verification**: Hash comparison pipeline to validate authenticity.
6. **Tamper Detection**: Instant alert mechanism for altered or unauthorized paper variants.
7. **Basic Audit Logging**: Append-only event tracking for all system interactions.
8. **Backup Question Bank Foundation**: Structured JSON fallback questions for emergency test generation.

---

## 📁 Project Structure

```text
Examshield/
│
├── backend/                  # Backend service modules and API logic
├── frontend/                 # User interface components
├── papers/
│   ├── original/             # Local storage for baseline examination papers (.gitignored)
│   └── leaked/               # Local storage for tamper simulation papers (.gitignored)
├── backup_questions/
│   └── questions.json        # Structured backup question-bank foundation
├── tests/                    # Unit and integration test suites
├── docs/                     # Project documentation & review artifacts
│   ├── requirements.md       # Functional & non-functional requirements
│   ├── architecture.md       # System architecture, schemas, and data flow
│   ├── test_cases.md         # Verification test matrix and validation plan
│   └── team_contributions.md # Review II team roles and progress tracking
│
├── README.md                 # Project documentation overview
├── requirements.txt          # Python dependencies
└── .gitignore                # Security and environment ignore rules
```

---

## 🔒 Security & Git Policies
- **Zero Sensitive Data in Git**: Real examination papers and PDF documents are strictly excluded from version control via `.gitignore`.
- **Directory Preservation**: `papers/original/` and `papers/leaked/` utilize `.gitkeep` markers to preserve folder hierarchy while ignoring file contents.
- **Local Isolation**: SQLite database files (`*.db`), virtual environments (`venv/`), and environment variables (`.env`) are strictly untracked.

---

## 📚 Documentation
- 📄 [Requirements Specification](docs/requirements.md)
- 🏗️ [Architecture & Schema](docs/architecture.md)
- 🧪 [Test Cases & Validation](docs/test_cases.md)
- 👥 [Team Contributions (Review II)](docs/team_contributions.md)

---

## 🚀 Setup & Installation

```bash
# 1. Clone the repository
git clone https://github.com/ananyapilania/Examshield.git
cd Examshield

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Frontend dependencies
cd frontend
npm install
cd ..
```

---

## 🔑 Initial Administrator Setup

ExamShield does not use insecure default credentials. Create your primary administrator account using the secure setup CLI:

```bash
# Interactive password prompt (recommended)
python -m backend.setup_admin --username security_admin --email admin@examshield.local

# Or pass password via environment variable / flag:
python -m backend.setup_admin --username security_admin --email admin@examshield.local --password "YourStrongPassword123!"
```

- Passwords are salted and hashed using **Argon2id**.
- Plaintext passwords are never stored in the database or logs.
- Duplicate administrative creation is automatically prevented.

---

## 👥 Role-Based Access Control (RBAC)

| Capability | Administrator (`ADMIN`) | Operational Staff (`STAFF`) |
|---|:---:|:---:|
| **Verify Candidate Papers** | ✅ | ✅ |
| **Inspect Permitted Examination Records** | ✅ | ✅ |
| **Register New Examination Papers** | ✅ | ❌ |
| **View Forensic Audit Logs** | ✅ | ❌ |
| **Manage User Accounts & Roles** | ✅ | ❌ |
| **Activate / Deactivate Accounts** | ✅ | ❌ |

---

## 🖥️ Running the Application

### 1. Start the FastAPI Backend
```bash
# Ensure virtual environment is active
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```
Backend API will be accessible at `http://127.0.0.1:8000`. API docs available at `http://127.0.0.1:8000/docs`.

### 2. Start the React Frontend
```bash
cd frontend
npm run dev
```
Frontend development server will be available at `http://localhost:5173`.

---

## 🧪 Running Automated Tests

```bash
# Run complete test suite (unit, integration, and security RBAC)
PYTHONPATH=. venv/bin/pytest -v
```

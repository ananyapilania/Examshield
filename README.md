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

# 3. Install dependencies
pip install -r requirements.txt
```

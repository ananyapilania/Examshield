import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ShieldCheck,
  UploadCloud,
  FileText,
  CheckCircle2,
  XCircle,
  LockKeyhole,
  Database,
  ScanSearch,
  Clock3,
  Hash,
  ChevronRight,
  RotateCcw,
  History,
  ShieldAlert,
  LoaderCircle,
  ExternalLink,
  PlusCircle,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  Filter,
  ArrowRight,
  Shield,
  Layers,
  LogOut,
  User,
  Users,
} from "lucide-react";
import "./index.css";
import {
  checkHealth,
  getRegisteredExams,
  registerExamPaper,
  verifyExamPaper,
  getAuditLogs,
  logout,
  getStoredUser,
  getCurrentUser,
  clearSession,
} from "./api";
import LoginView from "./LoginView";
import UserManagementView from "./UserManagementView";
import PermittedRecordsView from "./PermittedRecordsView";

const verificationSteps = [
  { label: "Document ingestion & byte stream", icon: ScanSearch },
  { label: "SHA-256 fingerprint computation", icon: Hash },
  { label: "Baseline database comparison", icon: Database },
  { label: "Audit trail event logging", icon: ShieldCheck },
];

function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [sessionNotice, setSessionNotice] = useState(null);
  const [activeTab, setActiveTab] = useState("verify"); // "verify" | "register" | "history" | "records" | "users"
  const [backendStatus, setBackendStatus] = useState("checking"); // "checking" | "online" | "offline"
  const [exams, setExams] = useState([]);
  const [loadingExams, setLoadingExams] = useState(false);

  // Verification state
  const [selectedExamId, setSelectedExamId] = useState("");
  const [verifyFile, setVerifyFile] = useState(null);
  const [verifyState, setVerifyState] = useState("idle"); // "idle" | "verifying" | "result" | "error"
  const [verifyProgress, setVerifyProgress] = useState(0);
  const [verifyStep, setVerifyStep] = useState(0);
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifyError, setVerifyError] = useState(null);

  // Registration state
  const [regForm, setRegForm] = useState({
    exam_id: "",
    exam_name: "",
    subject: "",
    academic_year: "2025-2026",
    paper_version: "Set-A",
  });
  const [regFile, setRegFile] = useState(null);
  const [regLoading, setRegLoading] = useState(false);
  const [regSuccess, setRegSuccess] = useState(null);
  const [regError, setRegError] = useState(null);

  // Audit Logs state
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditExamFilter, setAuditExamFilter] = useState("");
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState(null);

  // Session expiration event listener
  useEffect(() => {
    const handleExpired = (e) => {
      clearSession();
      setCurrentUser(null);
      setSessionNotice(e.detail?.message || "Session has expired. Please re-authenticate.");
    };
    window.addEventListener("examshield-session-expired", handleExpired);
    return () => window.removeEventListener("examshield-session-expired", handleExpired);
  }, []);

  // Validate active session with backend on initial mount
  useEffect(() => {
    if (currentUser) {
      getCurrentUser()
        .then((freshUser) => setCurrentUser(freshUser))
        .catch(() => {
          clearSession();
          setCurrentUser(null);
        });
    }
  }, []);

  // Health check on mount and periodic poll
  useEffect(() => {
    let isMounted = true;
    const testHealth = async () => {
      try {
        await checkHealth();
        if (isMounted) setBackendStatus("online");
      } catch (err) {
        if (isMounted) setBackendStatus("offline");
      }
    };
    testHealth();
    const interval = setInterval(testHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Fetch registered exams
  const fetchExams = async () => {
    setLoadingExams(true);
    try {
      const data = await getRegisteredExams();
      setExams(data);
      if (data.length > 0 && !selectedExamId) {
        setSelectedExamId(data[0].exam_id);
      }
    } catch (err) {
      console.error("Failed to load exams:", err);
    } finally {
      setLoadingExams(false);
    }
  };

  useEffect(() => {
    if (currentUser) {
      fetchExams();
    }
  }, [currentUser]);

  // Fetch audit logs when tab changes or filter updates (ADMIN only)
  const fetchLogs = async (filterId = auditExamFilter) => {
    if (!currentUser || currentUser.role !== "ADMIN") return;
    setAuditLoading(true);
    setAuditError(null);
    try {
      const logs = await getAuditLogs(filterId || null);
      setAuditLogs(logs);
    } catch (err) {
      setAuditError(err.message || "Failed to retrieve audit logs.");
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser && currentUser.role === "ADMIN" && activeTab === "history") {
      fetchLogs(auditExamFilter);
      fetchExams();
    }
  }, [currentUser, activeTab, auditExamFilter]);

  // Enforce role-based tab restriction
  useEffect(() => {
    if (currentUser && currentUser.role === "STAFF") {
      if (["register", "history", "users"].includes(activeTab)) {
        setActiveTab("verify");
      }
    }
  }, [currentUser, activeTab]);

  const handleLogout = async () => {
    await logout();
    clearSession();
    setCurrentUser(null);
    setSessionNotice(null);
    setActiveTab("verify");
  };

  // Handle document verification
  const handleVerify = async () => {
    if (!selectedExamId) {
      setVerifyError("Please select or enter an Exam ID to verify against.");
      return;
    }
    if (!verifyFile) {
      setVerifyError("Please select a candidate PDF file to verify.");
      return;
    }

    setVerifyState("verifying");
    setVerifyProgress(10);
    setVerifyStep(0);
    setVerifyError(null);

    // Simulate incremental visual stages while network request runs
    const progressTimer = setInterval(() => {
      setVerifyProgress((prev) => {
        if (prev < 80) {
          const next = prev + 15;
          setVerifyStep(Math.min(verificationSteps.length - 2, Math.floor(next / 25)));
          return next;
        }
        return prev;
      });
    }, 120);

    try {
      const response = await verifyExamPaper(selectedExamId, verifyFile);
      clearInterval(progressTimer);
      setVerifyProgress(100);
      setVerifyStep(verificationSteps.length - 1);
      setTimeout(() => {
        setVerifyResult(response);
        setVerifyState("result");
        fetchExams(); // Update statuses in background
      }, 400);
    } catch (err) {
      clearInterval(progressTimer);
      setVerifyError(err.message || "Paper verification failed. Please try again.");
      setVerifyState("error");
    }
  };

  // Reset verification workflow
  const resetVerification = () => {
    setVerifyFile(null);
    setVerifyState("idle");
    setVerifyProgress(0);
    setVerifyStep(0);
    setVerifyResult(null);
    setVerifyError(null);
  };

  // Handle exam registration (Admin only)
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regFile) {
      setRegError("Please select an original examination paper PDF.");
      return;
    }
    if (!regForm.exam_id.trim() || !regForm.exam_name.trim()) {
      setRegError("Exam ID and Exam Name are required.");
      return;
    }

    setRegLoading(true);
    setRegError(null);
    setRegSuccess(null);

    const formData = new FormData();
    formData.append("exam_id", regForm.exam_id.trim());
    formData.append("exam_name", regForm.exam_name.trim());
    formData.append("subject", regForm.subject.trim());
    formData.append("academic_year", regForm.academic_year.trim());
    formData.append("paper_version", regForm.paper_version.trim());
    formData.append("file", regFile);

    try {
      const result = await registerExamPaper(formData);
      setRegSuccess(result);
      setRegForm({
        exam_id: "",
        exam_name: "",
        subject: "",
        academic_year: "2025-2026",
        paper_version: "Set-A",
      });
      setRegFile(null);
      await fetchExams();
    } catch (err) {
      setRegError(err.message || "Failed to register examination paper.");
    } finally {
      setRegLoading(false);
    }
  };

  const jumpToVerificationForExam = (examId) => {
    setSelectedExamId(examId);
    resetVerification();
    setActiveTab("verify");
  };

  const jumpToAuditForExam = (examId) => {
    if (currentUser?.role === "ADMIN") {
      setAuditExamFilter(examId);
      setActiveTab("history");
    }
  };

  // If not authenticated, render Login Page
  if (!currentUser) {
    return (
      <LoginView
        backendStatus={backendStatus}
        sessionNotice={sessionNotice}
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          setSessionNotice(null);
          setActiveTab("verify");
          fetchExams();
        }}
      />
    );
  }

  const isAdmin = currentUser.role === "ADMIN";

  return (
    <div className="min-h-screen text-slate-100">
      {/* Top Sticky Header */}
      <header className="sticky top-0 z-20 border-b border-slate-800/70 bg-[#050b14]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          {/* Brand & Role Badge */}
          <div
            className="flex cursor-pointer items-center gap-3"
            onClick={() => setActiveTab("verify")}
          >
            <div className="grid size-10 place-items-center rounded-xl bg-blue-600/15 ring-1 ring-blue-400/20">
              <ShieldCheck className="size-6 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight">ExamShield</span>
                {isAdmin ? (
                  <span className="rounded-md border border-purple-400/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-bold tracking-wider text-purple-300">
                    ADMIN
                  </span>
                ) : (
                  <span className="rounded-md border border-blue-400/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-bold tracking-wider text-blue-300">
                    STAFF
                  </span>
                )}
              </div>
              <div className="text-[10px] uppercase tracking-[.22em] text-slate-500">
                Document Security Core
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1.5 rounded-xl border border-slate-800/60 bg-slate-950/40 p-1 text-sm">
            <button
              onClick={() => setActiveTab("verify")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 transition cursor-pointer ${
                activeTab === "verify"
                  ? "bg-blue-600 text-white shadow-sm font-medium"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`}
            >
              <ScanSearch className="size-4" />
              <span>Verify Document</span>
            </button>

            {isAdmin ? (
              <>
                <button
                  onClick={() => setActiveTab("register")}
                  className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 transition cursor-pointer ${
                    activeTab === "register"
                      ? "bg-blue-600 text-white shadow-sm font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  <PlusCircle className="size-4" />
                  <span>Register Paper</span>
                </button>

                <button
                  onClick={() => setActiveTab("history")}
                  className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 transition cursor-pointer ${
                    activeTab === "history"
                      ? "bg-blue-600 text-white shadow-sm font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  <History className="size-4" />
                  <span>Audit History</span>
                </button>

                <button
                  onClick={() => setActiveTab("users")}
                  className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 transition cursor-pointer ${
                    activeTab === "users"
                      ? "bg-blue-600 text-white shadow-sm font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  <Users className="size-4" />
                  <span>Manage Users</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => setActiveTab("records")}
                className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 transition cursor-pointer ${
                  activeTab === "records"
                    ? "bg-blue-600 text-white shadow-sm font-medium"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                <Database className="size-4" />
                <span>Permitted Records</span>
              </button>
            )}
          </nav>

          {/* Right Controls: User Profile + Sign Out + Status */}
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs">
              <User className="size-3.5 text-slate-400" />
              <span className="font-semibold text-slate-200">{currentUser.username}</span>
            </div>

            <button
              onClick={handleLogout}
              title="Sign Out of Session"
              className="flex items-center gap-1.5 rounded-xl border border-slate-800 hover:border-rose-500/30 bg-slate-900/60 hover:bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-rose-300 transition cursor-pointer"
            >
              <LogOut className="size-3.5 text-rose-400" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>

            {/* Backend Status Indicator */}
            <div className="hidden lg:flex items-center">
              {backendStatus === "online" ? (
                <div className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                  <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Online</span>
                </div>
              ) : backendStatus === "checking" ? (
                <div className="flex items-center gap-1.5 rounded-full border border-blue-400/20 bg-blue-400/10 px-2.5 py-1 text-[11px] font-medium text-blue-300">
                  <LoaderCircle className="size-3 spin-slow text-blue-400" />
                  <span>Connecting...</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 rounded-full border border-rose-400/20 bg-rose-400/10 px-2.5 py-1 text-[11px] font-medium text-rose-300">
                  <span className="size-1.5 rounded-full bg-rose-400" />
                  <span>Offline</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="grid-bg mx-auto min-h-[calc(100vh-73px)] max-w-7xl px-5 py-10 lg:px-8 lg:py-12">
        {activeTab === "verify" && (
          <VerifyView
            exams={exams}
            loadingExams={loadingExams}
            selectedExamId={selectedExamId}
            setSelectedExamId={setSelectedExamId}
            verifyFile={verifyFile}
            setVerifyFile={setVerifyFile}
            verifyState={verifyState}
            verifyProgress={verifyProgress}
            verifyStep={verifyStep}
            verifyResult={verifyResult}
            verifyError={verifyError}
            onVerify={handleVerify}
            onReset={resetVerification}
            onNavigateToRegister={() => setActiveTab("register")}
            onViewAuditForExam={jumpToAuditForExam}
            isAdmin={isAdmin}
          />
        )}

        {activeTab === "register" && isAdmin && (
          <RegisterView
            form={regForm}
            setForm={setRegForm}
            file={regFile}
            setFile={setRegFile}
            loading={regLoading}
            success={regSuccess}
            error={regError}
            onSubmit={handleRegister}
            onResetSuccess={() => setRegSuccess(null)}
            onVerifyPaper={jumpToVerificationForExam}
          />
        )}

        {activeTab === "history" && isAdmin && (
          <HistoryView
            exams={exams}
            auditLogs={auditLogs}
            filterExamId={auditExamFilter}
            setFilterExamId={setAuditExamFilter}
            loading={auditLoading}
            error={auditError}
            onRefresh={() => {
              fetchLogs(auditExamFilter);
              fetchExams();
            }}
            onVerifyExam={jumpToVerificationForExam}
          />
        )}

        {activeTab === "records" && (
          <PermittedRecordsView
            exams={exams}
            loading={loadingExams}
            onRefresh={fetchExams}
            onVerifyExam={jumpToVerificationForExam}
          />
        )}

        {activeTab === "users" && isAdmin && (
          <UserManagementView currentUser={currentUser} />
        )}

        {/* Global Footer */}
        <footer className="mx-auto mt-16 flex max-w-4xl flex-col gap-2 border-t border-slate-800/70 pt-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span>ExamShield • SHA-256 Cryptographic Integrity Core</span>
            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
              Role: {currentUser.role}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <LockKeyhole className="size-3.5 text-blue-400" />
            <span>FastAPI Backend Connected • SQLite Persistence</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

/* =========================================================================
   1. VERIFICATION VIEW & COMPONENTS
   ========================================================================= */

function VerifyView({
  exams,
  loadingExams,
  selectedExamId,
  setSelectedExamId,
  verifyFile,
  setVerifyFile,
  verifyState,
  verifyProgress,
  verifyStep,
  verifyResult,
  verifyError,
  onVerify,
  onReset,
  onNavigateToRegister,
  onViewAuditForExam,
  isAdmin = true,
}) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const chooseFile = (selected) => {
    if (!selected) return;
    if (
      selected.type !== "application/pdf" &&
      !selected.name.toLowerCase().endsWith(".pdf")
    ) {
      alert("Please select a valid PDF file.");
      return;
    }
    if (selected.size > 10 * 1024 * 1024) {
      alert("Please choose a PDF smaller than 10 MB.");
      return;
    }
    setVerifyFile(selected);
    onReset();
    setVerifyFile(selected);
  };

  return (
    <div>
      {/* Hero Header */}
      <section className="mx-auto max-w-4xl text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-400/15 bg-blue-400/5 px-3 py-1.5 text-xs font-medium text-blue-300">
          <LockKeyhole className="size-3.5" />
          Cryptographic paper integrity & tamper detection
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Verify an examination paper
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
          Upload a candidate PDF to compute its SHA-256 digital fingerprint,
          compare it against the registered baseline in SQLite, and inspect forensic verification results.
        </p>
      </section>

      {/* Main Interactive Stage */}
      <section className="mx-auto mt-10 max-w-4xl space-y-6">
        {/* Exam Target Selector Card */}
        <div className="glass rounded-2xl p-5 border border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl bg-blue-500/10 text-blue-400">
                <Layers className="size-5" />
              </div>
              <div>
                <label
                  htmlFor="exam-select"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-400"
                >
                  Select Registered Target Exam
                </label>
                <div className="text-xs text-slate-500">
                  Choose which baseline examination record to verify against
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {exams.length > 0 ? (
                <select
                  id="exam-select"
                  value={selectedExamId}
                  onChange={(e) => setSelectedExamId(e.target.value)}
                  disabled={verifyState === "verifying"}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {exams.map((ex) => (
                    <option key={ex.exam_id} value={ex.exam_id}>
                      {ex.exam_id} • {ex.exam_name} ({ex.paper_version})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-400/90">
                    No exams registered yet
                  </span>
                  {isAdmin ? (
                    <button
                      onClick={onNavigateToRegister}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600/20 border border-blue-500/30 px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-600/30 transition cursor-pointer"
                    >
                      <PlusCircle className="size-3.5" /> Register First Exam
                    </button>
                  ) : (
                    <span className="text-xs text-slate-400">
                      Contact an administrator to register papers.
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Verification Card / Progress / Result Display */}
        {verifyState === "result" && verifyResult ? (
          <ResultCard
            file={verifyFile}
            result={verifyResult}
            onReset={onReset}
            onViewAudit={isAdmin && onViewAuditForExam ? () => onViewAuditForExam(verifyResult.exam_id) : null}
          />
        ) : verifyState === "verifying" ? (
          <VerificationProgress
            file={verifyFile}
            progress={verifyProgress}
            step={verifyStep}
          />
        ) : (
          <div>
            {verifyError && (
              <div className="mb-4 flex items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
                <AlertTriangle className="size-5 shrink-0 text-rose-400" />
                <div className="flex-1">{verifyError}</div>
                <button
                  onClick={onReset}
                  className="text-xs font-semibold text-rose-300 underline hover:text-rose-200"
                >
                  Dismiss
                </button>
              </div>
            )}
            <UploadCard
              file={verifyFile}
              dragging={dragging}
              setDragging={setDragging}
              onFile={chooseFile}
              onBrowse={() => inputRef.current?.click()}
              onVerify={onVerify}
              inputRef={inputRef}
              onReset={onReset}
              disabled={!selectedExamId}
            />
          </div>
        )}
      </section>

      {/* Feature & Security Info Cards */}
      <section className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-3">
        <InfoCard
          icon={Hash}
          title="Cryptographic SHA-256"
          text="Calculates a 64-character deterministic digest. Even a 1-bit alteration flips over 50% of the hash (avalanche effect)."
        />
        <InfoCard
          icon={Database}
          title="Blockchain Readiness"
          text="Off-chain prototype in Part 1. Immutable decentralized ledger anchoring is scheduled for the Part 2 roadmap."
          badge="Planned"
        />
        <InfoCard
          icon={ShieldCheck}
          title="Forensic Audit Trail"
          text="Every verification attempt and hash mismatch is automatically committed to an immutable append-only audit log."
        />
      </section>
    </div>
  );
}

function UploadCard({
  file,
  dragging,
  setDragging,
  onFile,
  onBrowse,
  onVerify,
  inputRef,
  onReset,
  disabled,
}) {
  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    onFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="glass drop-glow rounded-3xl p-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-[22px] border-2 border-dashed px-6 py-14 text-center transition sm:px-12 ${
          dragging
            ? "border-blue-400 bg-blue-400/10"
            : "border-slate-700 bg-slate-950/30 hover:border-slate-600"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />

        {!file ? (
          <>
            <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-blue-500/10 ring-1 ring-blue-400/15">
              <UploadCloud className="size-8 text-blue-400" />
            </div>
            <h2 className="mt-5 text-lg font-semibold text-white">
              Drop candidate examination paper here
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              or select a PDF document from your computer
            </p>
            <button
              type="button"
              onClick={onBrowse}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-500"
            >
              <UploadCloud className="size-4" /> Browse PDF
            </button>
            <p className="mt-4 text-xs text-slate-600">
              PDF format • Maximum file size 10 MB
            </p>
          </>
        ) : (
          <>
            <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-emerald-400/10 ring-1 ring-emerald-400/15">
              <FileText className="size-8 text-emerald-400" />
            </div>
            <h2 className="mt-5 truncate px-4 text-lg font-semibold text-white">
              {file.name}
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              {formatBytes(file.size)} • PDF document ready for verification
            </p>
            <div className="mx-auto mt-6 flex max-w-md gap-3">
              <button
                type="button"
                onClick={onVerify}
                disabled={disabled}
                className="flex-1 inline-flex items-center justify-center rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Verify Authenticity <ChevronRight className="ml-1 inline size-4" />
              </button>
              <button
                type="button"
                onClick={onReset}
                className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-300 hover:bg-white/5"
              >
                Change
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function VerificationProgress({ file, progress, step }) {
  return (
    <div className="glass rounded-3xl p-7 sm:p-10">
      <div className="flex items-start gap-4">
        <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-blue-500/10 ring-1 ring-blue-400/15">
          <LoaderCircle className="size-6 text-blue-400 spin-slow" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[.18em] text-blue-300">
            FastAPI Pipeline Active
          </p>
          <h2 className="mt-1 text-xl font-semibold text-white">
            Analyzing {file?.name}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Streaming candidate bytes, computing SHA-256 hash, and verifying integrity against the database.
          </p>
        </div>
      </div>

      <div className="mt-8 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-150"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>Cryptographic Verification Pipeline</span>
        <span>{progress}%</span>
      </div>

      <div className="mt-8 space-y-3">
        {verificationSteps.map((item, i) => {
          const Icon = item.icon;
          const complete = i < step || progress === 100;
          const active = i === step && progress < 100;
          return (
            <div
              key={item.label}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
                complete
                  ? "border-emerald-400/15 bg-emerald-400/5"
                  : active
                  ? "border-blue-400/15 bg-blue-400/5"
                  : "border-slate-800 bg-slate-950/20"
              }`}
            >
              <div
                className={`grid size-8 place-items-center rounded-lg ${
                  complete
                    ? "bg-emerald-400/10 text-emerald-400"
                    : active
                    ? "bg-blue-400/10 text-blue-400"
                    : "bg-slate-800/70 text-slate-500"
                }`}
              >
                {complete ? (
                  <CheckCircle2 className="size-4" />
                ) : active ? (
                  <LoaderCircle className="size-4 spin-slow" />
                ) : (
                  <Icon className="size-4" />
                )}
              </div>
              <span
                className={`text-sm ${
                  complete || active ? "text-slate-200" : "text-slate-500"
                }`}
              >
                {item.label}
              </span>
              <span className="ml-auto text-xs text-slate-600">
                {complete ? "Complete" : active ? "Processing" : "Pending"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResultCard({ file, result, onReset, onViewAudit }) {
  const isVerified = result.status === "VERIFIED";
  const [copiedRegistered, setCopiedRegistered] = useState(false);
  const [copiedUploaded, setCopiedUploaded] = useState(false);

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === "registered") {
      setCopiedRegistered(true);
      setTimeout(() => setCopiedRegistered(false), 2000);
    } else {
      setCopiedUploaded(true);
      setTimeout(() => setCopiedUploaded(false), 2000);
    }
  };

  const formattedDate = result.timestamp
    ? new Date(result.timestamp).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "medium",
      })
    : new Date().toLocaleString();

  return (
    <div className="glass overflow-hidden rounded-3xl border border-slate-800">
      {/* Top Banner with Result State */}
      <div
        className={`border-b p-7 sm:p-9 ${
          isVerified
            ? "border-emerald-500/20 bg-emerald-500/[0.06]"
            : "border-rose-500/20 bg-rose-500/[0.08]"
        }`}
      >
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4">
            <div
              className={`grid size-14 place-items-center rounded-2xl ring-1 ${
                isVerified
                  ? "bg-emerald-400/10 ring-emerald-400/20 text-emerald-400"
                  : "bg-rose-400/10 ring-rose-400/20 text-rose-400"
              }`}
            >
              {isVerified ? (
                <CheckCircle2 className="size-8" />
              ) : (
                <ShieldAlert className="size-8" />
              )}
            </div>
            <div>
              <p
                className={`text-xs font-semibold uppercase tracking-[.18em] ${
                  isVerified ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                Verification Result
              </p>
              <h2 className="mt-1 text-2xl font-bold text-white">
                {isVerified
                  ? "Authentic Examination Paper"
                  : "Tamper Detected! Security Alert"}
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Exam ID:{" "}
                <span className="font-mono text-slate-200">{result.exam_id}</span> • File:{" "}
                <span className="text-slate-200">{file?.name || "Uploaded Document"}</span>
              </p>
            </div>
          </div>
          <div
            className={`self-start sm:self-center rounded-full border px-4 py-2 text-xs font-bold tracking-wider ${
              isVerified
                ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                : "border-rose-400/30 bg-rose-400/10 text-rose-300 animate-pulse"
            }`}
          >
            {result.status}
          </div>
        </div>
      </div>

      <div className="p-7 sm:p-9 space-y-6">
        {/* Real Cryptographic Hashes Comparison Box */}
        <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <Hash className="size-4 text-blue-400" />
              Cryptographic SHA-256 Hash Comparison
            </div>
            <span
              className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${
                isVerified
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                  : "border-rose-400/20 bg-rose-400/10 text-rose-300"
              }`}
            >
              {isVerified ? "Exact Match" : "Hash Mismatch"}
            </span>
          </div>

          {/* Baseline Hash */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Registered Baseline Hash:</span>
              <button
                onClick={() => copyToClipboard(result.registered_hash, "registered")}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition"
              >
                {copiedRegistered ? (
                  <>
                    <Check className="size-3 text-emerald-400" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="size-3" /> Copy
                  </>
                )}
              </button>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-2.5 font-mono text-xs text-slate-300 break-all select-all">
              {result.registered_hash}
            </div>
          </div>

          {/* Uploaded Candidate Hash */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Uploaded Candidate Hash:</span>
              <button
                onClick={() => copyToClipboard(result.uploaded_hash, "uploaded")}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition"
              >
                {copiedUploaded ? (
                  <>
                    <Check className="size-3 text-emerald-400" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="size-3" /> Copy
                  </>
                )}
              </button>
            </div>
            <div
              className={`rounded-xl border px-3.5 py-2.5 font-mono text-xs break-all select-all ${
                isVerified
                  ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-200"
                  : "border-rose-500/30 bg-rose-950/20 text-rose-200"
              }`}
            >
              {result.uploaded_hash}
            </div>
          </div>
        </div>

        {/* Status Rows */}
        <div className="grid gap-3 sm:grid-cols-2">
          <ResultRow
            icon={ShieldCheck}
            label="Document Integrity"
            value={isVerified ? "Valid & Unmodified" : "Compromised / Altered"}
            status={isVerified ? "success" : "flagged"}
          />
          <ResultRow
            icon={Hash}
            label="SHA-256 Digest Match"
            value={isVerified ? "Matches Baseline" : "Digest Mismatch"}
            status={isVerified ? "success" : "flagged"}
          />
          <ResultRow
            icon={Database}
            label="Blockchain Record"
            value="Planned (Off-chain Prototype)"
            status="planned"
            badge="Part 2 Roadmap"
          />
          <ResultRow
            icon={Clock3}
            label="Verification Timestamp"
            value={formattedDate}
            status="neutral"
          />
        </div>

        {/* Forensic Summary Callout */}
        <div
          className={`rounded-2xl border p-5 ${
            isVerified
              ? "border-emerald-500/20 bg-emerald-500/5 text-slate-300"
              : "border-rose-500/20 bg-rose-500/5 text-slate-300"
          }`}
        >
          <div className="flex items-center gap-2 text-sm font-semibold">
            {isVerified ? (
              <>
                <ShieldCheck className="size-4 text-emerald-400" />
                <span className="text-emerald-300">Forensic Integrity Confirmed</span>
              </>
            ) : (
              <>
                <ShieldAlert className="size-4 text-rose-400" />
                <span className="text-rose-300">Forensic Tampering Alert</span>
              </>
            )}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {isVerified
              ? "The uploaded document's cryptographic digest matches the registered baseline exactly. The file is authentic, untampered, and verified through the ExamShield SQLite persistence engine."
              : "Warning: The candidate paper's calculated SHA-256 hash does not match the registered baseline. Any alteration to content, formatting, or metadata triggers an avalanche effect in the digest."}
          </p>
          <div className="mt-3 text-xs text-slate-500">
            Audit log entry recorded with event timestamp:{" "}
            <span className="font-mono text-slate-400">{result.timestamp}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-white/5 transition cursor-pointer"
          >
            <RotateCcw className="size-4" /> Verify another document
          </button>
          {onViewAudit && (
            <button
              type="button"
              onClick={onViewAudit}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600/20 border border-blue-500/30 px-5 py-3 text-sm font-semibold text-blue-300 hover:bg-blue-600/30 transition cursor-pointer"
            >
              <History className="size-4" /> View in Audit Trail
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultRow({ icon: Icon, label, value, status, badge }) {
  let iconColor = "text-blue-400";
  let statusBadge = null;

  if (status === "success") {
    iconColor = "text-emerald-400";
    statusBadge = <CheckCircle2 className="ml-auto size-4 shrink-0 text-emerald-400" />;
  } else if (status === "flagged") {
    iconColor = "text-rose-400";
    statusBadge = <XCircle className="ml-auto size-4 shrink-0 text-rose-400" />;
  } else if (status === "planned") {
    iconColor = "text-amber-400";
    statusBadge = (
      <span className="ml-auto rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium text-amber-300 shrink-0">
        {badge || "Planned"}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/25 p-4">
      <Icon className={`size-4 ${iconColor} shrink-0`} />
      <div className="min-w-0 flex-1">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="mt-0.5 text-sm font-medium text-slate-200 truncate">{value}</div>
      </div>
      {statusBadge}
    </div>
  );
}

function InfoCard({ icon: Icon, title, text, badge }) {
  return (
    <div className="glass rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between">
          <Icon className="size-5 text-blue-400" />
          {badge && (
            <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium text-amber-300">
              {badge}
            </span>
          )}
        </div>
        <h3 className="mt-4 text-sm font-semibold text-slate-200">{title}</h3>
        <p className="mt-1.5 text-xs leading-5 text-slate-500">{text}</p>
      </div>
    </div>
  );
}

/* =========================================================================
   2. EXAM REGISTRATION VIEW
   ========================================================================= */

function RegisterView({
  form,
  setForm,
  file,
  setFile,
  loading,
  success,
  error,
  onSubmit,
  onResetSuccess,
  onVerifyPaper,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      if (
        selected.type !== "application/pdf" &&
        !selected.name.toLowerCase().endsWith(".pdf")
      ) {
        alert("Please select a PDF document.");
        return;
      }
      setFile(selected);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header */}
      <section className="text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-400/15 bg-blue-400/5 px-3 py-1.5 text-xs font-medium text-blue-300">
          <PlusCircle className="size-3.5" />
          Baseline Document Registration
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Register an Examination Paper
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-400">
          Ingest an original examination paper into ExamShield. The backend will compute its
          immutable SHA-256 digital fingerprint, store metadata in SQLite, and create an audit trail.
        </p>
      </section>

      {/* Success Notification Card */}
      {success && (
        <div className="glass rounded-3xl border border-emerald-500/20 bg-emerald-500/[0.04] p-6 sm:p-8 space-y-5">
          <div className="flex items-center gap-3">
            <div className="grid size-12 place-items-center rounded-2xl bg-emerald-400/10 text-emerald-400 ring-1 ring-emerald-400/20">
              <CheckCircle2 className="size-6" />
            </div>
            <div>
              <div className="text-xs uppercase font-semibold tracking-wider text-emerald-300">
                Registration Successful
              </div>
              <h3 className="text-xl font-bold text-white">{success.exam_name}</h3>
              <div className="text-xs text-slate-400">
                Exam ID: <span className="font-mono text-slate-200">{success.exam_id}</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 space-y-2">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Computed Baseline SHA-256 Digest:
            </div>
            <div className="font-mono text-xs text-emerald-300 break-all select-all">
              {success.file_hash}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 text-xs">
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
              <span className="text-slate-500 block">Subject:</span>
              <span className="font-medium text-slate-200">{success.subject}</span>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
              <span className="text-slate-500 block">Version / Set:</span>
              <span className="font-medium text-slate-200">{success.paper_version}</span>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
              <span className="text-slate-500 block">Status:</span>
              <span className="font-medium text-emerald-300">{success.status}</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              type="button"
              onClick={() => onVerifyPaper(success.exam_id)}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-500"
            >
              Verify Candidate Paper For This Exam <ArrowRight className="size-4" />
            </button>
            <button
              type="button"
              onClick={onResetSuccess}
              className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-semibold text-slate-300 hover:bg-white/5 transition"
            >
              Register Another Exam
            </button>
          </div>
        </div>
      )}

      {/* Registration Form */}
      {!success && (
        <form onSubmit={onSubmit} className="glass rounded-3xl border border-slate-800 p-6 sm:p-9 space-y-6">
          {error && (
            <div className="flex items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
              <AlertTriangle className="size-5 shrink-0 text-rose-400" />
              <div>{error}</div>
            </div>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            {/* Exam ID */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Exam Identifier (Unique ID) <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. EXAM-2026-CS101"
                value={form.exam_id}
                onChange={(e) => setForm({ ...form, exam_id: e.target.value })}
                className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-[11px] text-slate-500">
                Alphanumeric index for verification queries
              </p>
            </div>

            {/* Exam Name */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Exam Name / Title <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Operating Systems Final"
                value={form.exam_name}
                onChange={(e) => setForm({ ...form, exam_name: e.target.value })}
                className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Subject */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Subject / Course Code <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. CSE-301"
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Academic Year & Set */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                  Academic Year
                </label>
                <input
                  type="text"
                  required
                  placeholder="2025-2026"
                  value={form.academic_year}
                  onChange={(e) => setForm({ ...form, academic_year: e.target.value })}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                  Paper Set / Version
                </label>
                <input
                  type="text"
                  required
                  placeholder="Set-A"
                  value={form.paper_version}
                  onChange={(e) => setForm({ ...form, paper_version: e.target.value })}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* PDF Upload Field */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Original Examination Paper (PDF) <span className="text-rose-400">*</span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            {!file ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-700 bg-slate-950/30 p-8 text-center transition hover:border-slate-500"
              >
                <UploadCloud className="mx-auto size-8 text-slate-400" />
                <p className="mt-3 text-sm font-medium text-slate-200">
                  Click to select original examination PDF
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  PDF document • Will be hashed via SHA-256 upon submission
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                <div className="flex items-center gap-3">
                  <FileText className="size-6 text-emerald-400" />
                  <div>
                    <div className="text-sm font-semibold text-white">{file.name}</div>
                    <div className="text-xs text-slate-500">{formatBytes(file.size)}</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Change File
                </button>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <LoaderCircle className="size-4 spin-slow" /> Hashing and Registering...
              </>
            ) : (
              <>
                <ShieldCheck className="size-4" /> Register Examination Paper
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
}

/* =========================================================================
   3. AUDIT HISTORY & REGISTERED EXAMS VIEW
   ========================================================================= */

function HistoryView({
  exams,
  auditLogs,
  filterExamId,
  setFilterExamId,
  loading,
  error,
  onRefresh,
  onVerifyExam,
}) {
  const [subTab, setSubTab] = useState("audit"); // "audit" | "exams"

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-blue-400/15 bg-blue-400/5 px-3 py-1 text-xs font-medium text-blue-300">
            <History className="size-3.5" />
            Append-Only SQLite Audit Trail
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            System Records & Forensic History
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Real immutable events and examination records retrieved directly from the FastAPI backend.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 transition"
          >
            <RefreshCw className={`size-3.5 ${loading ? "spin-slow text-blue-400" : ""}`} />
            Refresh Records
          </button>
        </div>
      </section>

      {/* Sub Tabs */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
        <button
          onClick={() => setSubTab("audit")}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
            subTab === "audit"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
          }`}
        >
          Audit Events ({auditLogs.length})
        </button>
        <button
          onClick={() => setSubTab("exams")}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
            subTab === "exams"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
          }`}
        >
          Registered Exams ({exams.length})
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          <AlertTriangle className="size-5 shrink-0 text-rose-400" />
          <div>{error}</div>
        </div>
      )}

      {/* Audit Logs Table */}
      {subTab === "audit" && (
        <div className="glass rounded-3xl border border-slate-800 overflow-hidden">
          {/* Filter Bar */}
          <div className="border-b border-slate-800/80 bg-slate-950/40 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <Filter className="size-4 text-blue-400" />
              Filter by Examination ID
            </div>
            <select
              value={filterExamId}
              onChange={(e) => setFilterExamId(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Examinations</option>
              {exams.map((ex) => (
                <option key={ex.exam_id} value={ex.exam_id}>
                  {ex.exam_id} ({ex.exam_name})
                </option>
              ))}
            </select>
          </div>

          {auditLogs.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <History className="mx-auto size-8 text-slate-600 mb-2" />
              <p className="text-sm">No audit logs found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Exam ID</th>
                    <th className="px-5 py-3.5">Action</th>
                    <th className="px-5 py-3.5">Result</th>
                    <th className="px-5 py-3.5">Timestamp</th>
                    <th className="px-5 py-3.5">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {auditLogs.map((log) => {
                    const isFlagged = log.result === "FLAGGED" || log.action === "HASH_MISMATCH";
                    return (
                      <tr
                        key={log.event_id || log.timestamp}
                        className={`transition hover:bg-slate-900/40 ${
                          isFlagged ? "bg-rose-950/10" : ""
                        }`}
                      >
                        <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                          #{log.event_id}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-xs font-semibold text-slate-300">
                          {log.exam_id}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="rounded-lg bg-slate-800/80 px-2 py-1 text-xs font-mono text-slate-200">
                            {log.action}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <span
                            className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                              isFlagged
                                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                            }`}
                          >
                            {log.result}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-xs text-slate-400 whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleString(undefined, {
                            dateStyle: "short",
                            timeStyle: "medium",
                          })}
                        </td>
                        <td className="px-5 py-3.5 text-xs text-slate-400 max-w-md break-words">
                          {log.details || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Registered Exams Table */}
      {subTab === "exams" && (
        <div className="glass rounded-3xl border border-slate-800 overflow-hidden">
          {exams.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Database className="mx-auto size-8 text-slate-600 mb-2" />
              <p className="text-sm">No registered exams found in the SQLite database.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-5 py-3.5">Exam ID</th>
                    <th className="px-5 py-3.5">Title</th>
                    <th className="px-5 py-3.5">Subject</th>
                    <th className="px-5 py-3.5">Version</th>
                    <th className="px-5 py-3.5">Baseline SHA-256 Digest</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {exams.map((ex) => (
                    <tr key={ex.exam_id} className="transition hover:bg-slate-900/40">
                      <td className="px-5 py-3.5 font-mono text-xs font-semibold text-blue-400">
                        {ex.exam_id}
                      </td>
                      <td className="px-5 py-3.5 font-medium text-white">{ex.exam_name}</td>
                      <td className="px-5 py-3.5 text-xs text-slate-300">{ex.subject}</td>
                      <td className="px-5 py-3.5 text-xs text-slate-400">{ex.paper_version}</td>
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-400 max-w-xs truncate">
                        <span title={ex.file_hash}>
                          {ex.file_hash ? `${ex.file_hash.slice(0, 16)}...${ex.file_hash.slice(-8)}` : "—"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                            ex.status === "VERIFIED"
                              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                              : ex.status === "TAMPER_DETECTED"
                              ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                              : "border-blue-500/30 bg-blue-500/10 text-blue-300"
                          }`}
                        >
                          {ex.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => onVerifyExam(ex.exam_id)}
                          className="inline-flex items-center gap-1 rounded-lg bg-blue-600/20 border border-blue-500/30 px-3 py-1.5 text-xs font-medium text-blue-300 hover:bg-blue-600/30 transition"
                        >
                          Verify Candidate Paper <ChevronRight className="size-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* =========================================================================
   UTILITY FUNCTIONS
   ========================================================================= */

function formatBytes(bytes) {
  if (!bytes) return "0 Bytes";
  const units = ["Bytes", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`;
}

createRoot(document.getElementById("root")).render(<App />);

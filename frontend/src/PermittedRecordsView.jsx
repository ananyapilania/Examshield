import React from "react";
import { Database, RefreshCw, ChevronRight } from "lucide-react";

/**
 * ExamShield Staff Permitted Records View
 * Provides staff with access to authorized examination records
 * for paper verification workflows without administrative audit exposure.
 */
export default function PermittedRecordsView({
  exams,
  loading,
  onRefresh,
  onVerifyExam,
}) {
  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-blue-400/15 bg-blue-400/5 px-3 py-1 text-xs font-medium text-blue-300">
            <Database className="size-3.5" />
            Operational Staff Access
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Permitted Examination Papers
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Active baseline documents authorized for verification and candidate paper authenticity checks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 transition cursor-pointer"
          >
            <RefreshCw className={`size-3.5 ${loading ? "spin-slow text-blue-400" : ""}`} />
            Refresh Records
          </button>
        </div>
      </section>

      {/* Table Card */}
      <div className="glass rounded-3xl border border-slate-800 overflow-hidden">
        {exams.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Database className="mx-auto size-8 text-slate-600 mb-2" />
            <p className="text-sm">No registered examination papers available.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 font-semibold">
                <tr>
                  <th className="px-5 py-3.5">Exam ID</th>
                  <th className="px-5 py-3.5">Exam Name</th>
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
                        {ex.file_hash
                          ? `${ex.file_hash.slice(0, 16)}...${ex.file_hash.slice(-8)}`
                          : "—"}
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
                        className="inline-flex items-center gap-1 rounded-lg bg-blue-600/20 border border-blue-500/30 px-3 py-1.5 text-xs font-medium text-blue-300 hover:bg-blue-600/30 transition cursor-pointer"
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
    </div>
  );
}

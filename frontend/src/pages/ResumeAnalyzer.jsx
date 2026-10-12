import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";

const ResumeAnalyzerPage = () => {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [expandedSkill, setExpandedSkill] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
    },
  });

  const connectToProgressStream = (sessionId) => {
    const eventSource = new EventSource(`http://localhost:8000/resume/stream?session_id=${sessionId}`);
    eventSource.onmessage = (event) => {
      setProgress(event.data);
      if (event.data === "Completed" || event.data.startsWith("Error")) {
        eventSource.close();
      }
    };
    eventSource.onerror = () => {
      eventSource.close();
    };
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF file to analyze");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const sessionId = "job_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7);
      connectToProgressStream(sessionId);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_id", sessionId);
      if (jobDescription.trim()) {
        formData.append("job_description", jobDescription.trim());
      }

      const response = await fetch("http://localhost:8000/resume/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to analyze resume");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to analyze resume. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const getScoreBgColor = (score) => {
    if (score >= 80) return "bg-green-900/20 border-green-700";
    if (score >= 60) return "bg-yellow-900/20 border-yellow-700";
    return "bg-red-900/20 border-red-700";
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "matched":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "partially_matched":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "unverifiable":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      case "missing":
      default:
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col h-full w-full gap-4 p-4"
    >
      {/* Header section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex rounded-3xl border border-white/10 bg-slate-950/80 p-8 w-full shadow-2xl shadow-cyan-500/10 backdrop-blur-xl"
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full items-center">
          <div className="w-full flex flex-col gap-3">
            <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-1.5 text-sm text-cyan-200 shadow-sm w-fit">
              <span className="text-base">✨</span>
              <span>Evidence-Based Match & Deterministic Rubric</span>
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-white">
              Smart resume review with grounded proof.
            </h1>
            <p className="max-w-2xl text-slate-300 text-base">
              Upload your PDF resume and optionally paste a job description. We verify candidate experience against actual document evidence—no AI hallucinations, no arbitrary scores.
            </p>
          </div>

          <div className="grid gap-3 grid-cols-3">
            {[
              { label: "Scoring Engine", value: "Weighted Rubric" },
              { label: "Anti-Hallucination", value: "Page Citations" },
              { label: "Evidence", value: "Verified Text" },
            ].map((item) => (
              <motion.div
                key={item.label}
                whileHover={{ y: -4 }}
                className="rounded-3xl border border-white/10 bg-slate-900/80 p-4 text-center shadow-lg flex flex-col gap-1 items-center justify-center"
              >
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  {item.label}
                </p>
                <p className="mt-1 text-lg font-semibold text-white">
                  {item.value}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* Input section: PDF Dropzone + Job Description */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="grid gap-4 grid-cols-1 lg:grid-cols-2"
      >
        {/* Left: Upload Resume */}
        <div className="flex flex-col h-full w-full gap-4">
          <motion.div
            layout
            className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl flex flex-col gap-4"
          >
            <div>
              <h2 className="text-2xl font-semibold text-white">1. Upload Resume</h2>
              <p className="text-sm text-slate-400 mt-1">
                Drag & drop your PDF resume. We parse and index page-by-page.
              </p>
            </div>

            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-3xl p-6 flex flex-col items-center justify-center gap-3 text-center transition-all duration-300 ${
                isDragActive
                  ? "border-cyan-400 bg-slate-900/90 shadow-[0_18px_60px_-42px_rgba(59,130,246,0.8)]"
                  : "border-slate-700 bg-slate-950/40"
              } cursor-pointer hover:border-cyan-400`}
            >
              <input {...getInputProps()} />
              <span className="text-4xl">📄</span>
              <div>
                <p className="text-lg font-semibold text-white">
                  {file ? file.name : "Select or Drop PDF Resume"}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {file
                    ? `${(file.size / 1024).toFixed(1)} KB — Ready to analyze`
                    : "Supports multi-page searchable PDFs"}
                </p>
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={loading || !file}
              className={`w-full rounded-2xl py-4 text-sm font-semibold uppercase tracking-[0.18em] transition duration-300 ${
                loading || !file
                  ? "cursor-not-allowed bg-slate-800 text-slate-500"
                  : "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-xl shadow-cyan-500/20 hover:brightness-110"
              }`}
            >
              {loading ? (
                <div className="flex items-center justify-center gap-3">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                  Analyzing Evidence...
                </div>
              ) : jobDescription.trim() ? (
                "Run Targeted Job Match"
              ) : (
                "Run ATS Structure Audit"
              )}
            </button>
          </motion.div>

          <AnimatePresence>
            {progress && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.24 }}
                className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                      Processing Pipeline
                    </p>
                    <p className="mt-1 text-sm font-medium text-white">{progress}</p>
                  </div>
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
                    ⏳
                  </span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-500"
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 1.5, ease: "linear" }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right: Job Description Input */}
        <motion.div
          layout
          className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-white">2. Target Job Description</h2>
              <p className="text-sm text-slate-400 mt-1">
                Optional: Paste role requirements for deterministic weighted matching.
              </p>
            </div>
            {jobDescription && (
              <button
                onClick={() => setJobDescription("")}
                className="text-xs text-slate-400 hover:text-slate-200 underline"
              >
                Clear
              </button>
            )}
          </div>

          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste Job Description here (e.g. Required Qualifications, Technical Skills, Responsibilities)..."
            rows={8}
            className="w-full flex-1 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 resize-none"
          />

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5 text-xs text-slate-400 flex items-center gap-3">
            <span className="text-lg">⚖️</span>
            <span>
              <strong>Scoring Rubric:</strong> Required skills contribute 70%, preferred contribute 30%. Matched skills require verified citations from your PDF.
            </span>
          </div>
        </motion.div>
      </motion.section>

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="rounded-3xl border border-red-500/20 bg-red-950/70 p-6 text-white shadow-lg shadow-red-500/10"
          >
            <p className="font-semibold text-red-300">Analysis Error</p>
            <p className="mt-1 text-sm text-slate-200">{error}</p>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Results Section */}
      {result && (
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="space-y-6"
        >
          {/* Header Summary */}
          <motion.div
            layout
            className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">
                  {result.job_match ? "Job-Specific Evidence Match" : "General ATS Structural Review"}
                </p>
                <h2 className="mt-1 text-3xl font-semibold text-white">
                  Match & Qualification Report
                </h2>
              </div>
              <div className="rounded-2xl bg-slate-900/90 px-5 py-3 text-sm text-slate-300 border border-slate-800">
                Mode: <span className="font-semibold text-cyan-400">{result.metadata?.mode || "Standard"}</span>
              </div>
            </div>
          </motion.div>

          {/* Score Card */}
          <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
            <motion.div
              layout
              className={`${getScoreBgColor(result.ats_score)} lg:col-span-1 rounded-3xl border p-8 text-center shadow-xl flex flex-col justify-center items-center`}
            >
              <p className="text-xs uppercase tracking-[0.2em] text-slate-300 font-medium">
                {result.job_match ? "Deterministic Match Score" : "ATS Structural Readiness"}
              </p>
              <p className={`mt-3 text-6xl font-bold ${getScoreColor(result.ats_score)}`}>
                {result.ats_score}
              </p>
              <p className="mt-3 text-sm text-slate-300 max-w-xs">
                {result.ats_score >= 80
                  ? "High alignment with verified qualifications."
                  : result.ats_score >= 60
                  ? "Moderate alignment; addressing identified gaps will improve score."
                  : "Critical requirements missing or unverified."}
              </p>
            </motion.div>

            {/* Score breakdown component */}
            <motion.div
              layout
              className="lg:col-span-2 rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl flex flex-col justify-between"
            >
              <div>
                <h3 className="text-xl font-semibold text-white">Rubric Breakdown</h3>
                <p className="text-xs text-slate-400 mt-1">
                  {result.job_match?.score_breakdown?.summary || "Evaluated structural completeness and quantifiable achievements."}
                </p>
              </div>

              {result.job_match?.score_breakdown ? (
                <div className="grid grid-cols-2 gap-4 my-4">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-400">Required Skills Pool (70 max)</p>
                    <p className="text-2xl font-semibold text-cyan-300 mt-1">
                      {result.job_match.score_breakdown.required_score} <span className="text-sm text-slate-400">/ 70 pts</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Matched: {result.job_match.score_breakdown.required_matched_count}/{result.job_match.score_breakdown.required_total_count}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-400">Preferred Skills Pool (30 max)</p>
                    <p className="text-2xl font-semibold text-blue-300 mt-1">
                      {result.job_match.score_breakdown.preferred_score} <span className="text-sm text-slate-400">/ 30 pts</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Matched: {result.job_match.score_breakdown.preferred_matched_count}/{result.job_match.score_breakdown.preferred_total_count}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 my-4">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-400">Total Words Analyzed</p>
                    <p className="text-2xl font-semibold text-white mt-1">{result.metadata?.total_words || "N/A"}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-400">Pages Evaluated</p>
                    <p className="text-2xl font-semibold text-white mt-1">{result.metadata?.page_count || 1}</p>
                  </div>
                </div>
              )}

              <p className="text-xs text-slate-500 font-mono">
                Formula: {result.job_match?.score_breakdown?.rubric_formula || "ATS Sections (35) + Contact (15) + Impact Verbs & Numbers (30) + Density (20)"}
              </p>
            </motion.div>
          </div>

          {/* Job Match Skills & Evidence Drawer */}
          {result.job_match?.skills_analysis && result.job_match.skills_analysis.length > 0 && (
            <motion.div
              layout
              className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-white">Skills & Evidence Citations</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Click any skill to view verbatim quotes and page numbers verified in the uploaded resume.
                  </p>
                </div>
                <span className="text-xs text-slate-400 bg-slate-900 px-3 py-1.5 rounded-full border border-slate-800">
                  {result.job_match.skills_analysis.length} Requirements Evaluated
                </span>
              </div>

              <div className="grid gap-3">
                {result.job_match.skills_analysis.map((item, index) => {
                  const isExpanded = expandedSkill === index;
                  return (
                    <div
                      key={index}
                      className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 transition-all"
                    >
                      <button
                        onClick={() => setExpandedSkill(isExpanded ? null : index)}
                        className="w-full flex items-center justify-between text-left gap-4"
                      >
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-base font-medium text-white">{item.skill}</span>
                          <span className="text-xs uppercase px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-medium">
                            {item.category}
                          </span>
                          <span className={`text-xs uppercase px-2.5 py-0.5 rounded-full border font-semibold ${getStatusBadge(item.status)}`}>
                            {item.status.replace("_", " ")}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400 font-mono">
                          {isExpanded ? "▲ Hide Evidence" : "▼ View Citations"}
                        </span>
                      </button>

                      {item.reasoning && (
                        <p className="text-xs text-slate-400 mt-2">{item.reasoning}</p>
                      )}

                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-3 pt-3 border-t border-slate-800/80"
                          >
                            {item.evidence && item.evidence.length > 0 ? (
                              <div className="space-y-2">
                                <p className="text-xs uppercase font-semibold text-slate-400">Verbatim Resume Evidence:</p>
                                {item.evidence.map((ev, evIdx) => (
                                  <div
                                    key={evIdx}
                                    className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-300"
                                  >
                                    <div className="flex items-center justify-between mb-1.5">
                                      <span className="inline-flex items-center gap-1.5 font-medium text-cyan-400">
                                        📄 Page {ev.page}
                                      </span>
                                      <span className={`text-xs px-2 py-0.5 rounded ${ev.verified ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"}`}>
                                        {ev.verified ? "✓ Verified in PDF" : "✗ Unverified in PDF"}
                                      </span>
                                    </div>
                                    <p className="font-mono text-slate-300 italic">"{ev.snippet}"</p>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-rose-400 italic">
                                No evidence snippet found in candidate resume.
                              </p>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* Prioritized Suggestions & Gaps */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Actionable Suggestions */}
            <motion.div
              layout
              className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl"
            >
              <div className="mb-4 flex items-center gap-3">
                <span className="text-2xl">💡</span>
                <h3 className="text-xl font-semibold text-white">Prioritized Improvements</h3>
              </div>
              <ul className="space-y-3 text-sm text-slate-300">
                {(result.job_match?.prioritized_suggestions?.length
                  ? result.job_match.prioritized_suggestions.map((s) => s.suggestion)
                  : result.suggestions || []
                ).map((item, index) => (
                  <li key={index} className="flex gap-3">
                    <span className="text-cyan-400 font-bold">#{index + 1}</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* Identified Gaps or Strengths */}
            <motion.div
              layout
              className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl"
            >
              <div className="mb-4 flex items-center gap-3">
                <span className="text-2xl">🎯</span>
                <h3 className="text-xl font-semibold text-white">
                  {result.job_match ? "Skill Gaps & Remediation" : "Identified Strengths"}
                </h3>
              </div>
              {result.job_match?.gaps && result.job_match.gaps.length > 0 ? (
                <div className="space-y-3">
                  {result.job_match.gaps.map((gap, index) => (
                    <div key={index} className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-3 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-white">{gap.skill}</span>
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${gap.severity === "critical" ? "bg-rose-500/20 text-rose-300" : "bg-amber-500/20 text-amber-300"}`}>
                          {gap.severity.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-slate-400">{gap.recommendation}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <ul className="space-y-3 text-sm text-slate-300">
                  {(result.strengths || []).map((item, index) => (
                    <li key={index} className="flex gap-3">
                      <span className="text-emerald-400">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          </div>
        </motion.section>
      )}
    </motion.div>
  );
};

export default ResumeAnalyzerPage;

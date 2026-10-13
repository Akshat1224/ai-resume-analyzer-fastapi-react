import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { config } from "../config";

const ResumeComparePage = () => {
  const [fileV1, setFileV1] = useState(null);
  const [fileV2, setFileV2] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const onDropV1 = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFileV1(acceptedFiles[0]);
      setError("");
    }
  }, []);

  const onDropV2 = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFileV2(acceptedFiles[0]);
      setError("");
    }
  }, []);

  const { getRootProps: getRootPropsV1, getInputProps: getInputPropsV1, isDragActive: isDragActiveV1 } = useDropzone({
    onDrop: onDropV1,
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
  });

  const { getRootProps: getRootPropsV2, getInputProps: getInputPropsV2, isDragActive: isDragActiveV2 } = useDropzone({
    onDrop: onDropV2,
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
  });

  const handleCompare = async () => {
    if (!fileV1 || !fileV2) {
      setError("Please select both PDF files to compare");
      return;
    }
    if (!jobDescription.trim()) {
      setError("Please provide a job description for comparison");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const formData = new FormData();
      formData.append("file_v1", fileV1);
      formData.append("file_v2", fileV2);
      formData.append("job_description", jobDescription.trim());

      const response = await fetch(`${config.apiUrl}/resume/compare`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to compare resumes");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to compare resumes. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getDeltaColor = (delta) => {
    if (delta > 0) return "text-green-400";
    if (delta < 0) return "text-red-400";
    return "text-slate-400";
  };

  const getDeltaBg = (delta) => {
    if (delta > 0) return "bg-green-900/20 border-green-700";
    if (delta < 0) return "bg-red-900/20 border-red-700";
    return "bg-slate-900/20 border-slate-700";
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col h-full w-full gap-4 p-4"
    >
      {/* Header */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex rounded-3xl border border-white/10 bg-slate-950/80 p-8 w-full shadow-2xl shadow-cyan-500/10 backdrop-blur-xl"
      >
        <div className="w-full">
          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-1.5 text-sm text-cyan-200 shadow-sm w-fit mb-4">
            <span className="text-base">📊</span>
            <span>Version Comparison</span>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-white">
            Compare Resume Versions
          </h1>
          <p className="max-w-2xl text-slate-300 text-base mt-2">
            Upload two versions of your resume and a job description to detect score changes, newly verified skills, removed evidence, and unsupported claims.
          </p>
        </div>
      </motion.section>

      {/* Input Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="grid gap-4 grid-cols-1 lg:grid-cols-2"
      >
        {/* V1 Upload */}
        <div className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl">
          <div>
            <h2 className="text-2xl font-semibold text-white">Version 1 (Base)</h2>
            <p className="text-sm text-slate-400 mt-1">Original resume version</p>
          </div>
          <div
            {...getRootPropsV1()}
            className={`border-2 border-dashed rounded-3xl p-6 flex flex-col items-center justify-center gap-3 text-center transition-all duration-300 ${
              isDragActiveV1
                ? "border-cyan-400 bg-slate-900/90 shadow-[0_18px_60px_-42px_rgba(59,130,246,0.8)]"
                : "border-slate-700 bg-slate-950/40"
            } cursor-pointer hover:border-cyan-400`}
          >
            <input {...getInputPropsV1()} />
            <span className="text-4xl">📄</span>
            <div>
              <p className="text-lg font-semibold text-white">
                {fileV1 ? fileV1.name : "Select or Drop V1 PDF"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {fileV1 ? `${(fileV1.size / 1024).toFixed(1)} KB` : "Base version"}
              </p>
            </div>
          </div>
        </div>

        {/* V2 Upload */}
        <div className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl">
          <div>
            <h2 className="text-2xl font-semibold text-white">Version 2 (Updated)</h2>
            <p className="text-sm text-slate-400 mt-1">Revised resume version</p>
          </div>
          <div
            {...getRootPropsV2()}
            className={`border-2 border-dashed rounded-3xl p-6 flex flex-col items-center justify-center gap-3 text-center transition-all duration-300 ${
              isDragActiveV2
                ? "border-cyan-400 bg-slate-900/90 shadow-[0_18px_60px_-42px_rgba(59,130,246,0.8)]"
                : "border-slate-700 bg-slate-950/40"
            } cursor-pointer hover:border-cyan-400`}
          >
            <input {...getInputPropsV2()} />
            <span className="text-4xl">📄</span>
            <div>
              <p className="text-lg font-semibold text-white">
                {fileV2 ? fileV2.name : "Select or Drop V2 PDF"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {fileV2 ? `${(fileV2.size / 1024).toFixed(1)} KB` : "Updated version"}
              </p>
            </div>
          </div>
        </div>
      </motion.section>

      {/* Job Description */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-semibold text-white">Target Job Description</h2>
            <p className="text-sm text-slate-400 mt-1">Both versions will be evaluated against this job</p>
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
          placeholder="Paste Job Description here..."
          rows={6}
          className="w-full rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 resize-none"
        />
      </motion.section>

      {/* Compare Button */}
      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        onClick={handleCompare}
        disabled={loading || !fileV1 || !fileV2}
        className={`w-full rounded-2xl py-4 text-sm font-semibold uppercase tracking-[0.18em] transition duration-300 ${
          loading || !fileV1 || !fileV2
            ? "cursor-not-allowed bg-slate-800 text-slate-500"
            : "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-xl shadow-cyan-500/20 hover:brightness-110"
        }`}
      >
        {loading ? (
          <div className="flex items-center justify-center gap-3">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
            Comparing Versions...
          </div>
        ) : (
          "Compare Resume Versions"
        )}
      </motion.button>

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
            <p className="font-semibold text-red-300">Comparison Error</p>
            <p className="mt-1 text-sm text-slate-200">{error}</p>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Results */}
      {result && (
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6"
        >
          {/* Score Delta Card */}
          <motion.div
            layout
            className={`${getDeltaBg(result.score_delta)} rounded-3xl border p-8 text-center shadow-xl`}
          >
            <p className="text-xs uppercase tracking-[0.2em] text-slate-300 font-medium">
              Score Change
            </p>
            <p className={`mt-3 text-6xl font-bold ${getDeltaColor(result.score_delta)}`}>
              {result.score_delta > 0 ? "+" : ""}{result.score_delta}
            </p>
            <p className="mt-3 text-sm text-slate-300">
              V1: {result.base_version_score} → V2: {result.target_version_score}
            </p>
          </motion.div>

          {/* Verdict */}
          <motion.div
            layout
            className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl"
          >
            <h3 className="text-xl font-semibold text-white mb-3">Verdict</h3>
            <p className="text-slate-300">{result.verdict}</p>
          </motion.div>

          {/* Changes Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Added Skills */}
            {result.added_skills.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-green-500/20 bg-green-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-green-300 mb-3">
                  ✓ Newly Verified Skills ({result.added_skills.length})
                </h3>
                <ul className="space-y-2">
                  {result.added_skills.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-green-400">+</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Removed Skills */}
            {result.removed_skills.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-red-500/20 bg-red-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-red-300 mb-3">
                  ✗ Dropped Skills ({result.removed_skills.length})
                </h3>
                <ul className="space-y-2">
                  {result.removed_skills.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-red-400">-</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Unsupported Claims */}
            {result.unsupported_claims.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-purple-500/20 bg-purple-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-purple-300 mb-3">
                  ⚠ Unsupported Claims ({result.unsupported_claims.length})
                </h3>
                <ul className="space-y-2">
                  {result.unsupported_claims.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-purple-400">!</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Removed Evidence */}
            {result.removed_evidence.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-amber-500/20 bg-amber-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-amber-300 mb-3">
                  📉 Reduced Evidence ({result.removed_evidence.length})
                </h3>
                <ul className="space-y-2">
                  {result.removed_evidence.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-amber-400">↓</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Gaps Resolved */}
            {result.gaps_resolved.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-emerald-500/20 bg-emerald-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-emerald-300 mb-3">
                  ✅ Gaps Resolved ({result.gaps_resolved.length})
                </h3>
                <ul className="space-y-2">
                  {result.gaps_resolved.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-emerald-400">✓</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* New Gaps */}
            {result.new_gaps.length > 0 && (
              <motion.div
                layout
                className="rounded-3xl border border-rose-500/20 bg-rose-950/20 p-6 shadow-xl"
              >
                <h3 className="text-xl font-semibold text-rose-300 mb-3">
                  ❌ New Gaps ({result.new_gaps.length})
                </h3>
                <ul className="space-y-2">
                  {result.new_gaps.map((skill, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <span className="text-rose-400">×</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </div>

          {/* Retained Skills */}
          {result.retained_skills.length > 0 && (
            <motion.div
              layout
              className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl"
            >
              <h3 className="text-xl font-semibold text-slate-300 mb-3">
                Retained Core Skills ({result.retained_skills.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.retained_skills.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-sm"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </motion.section>
      )}
    </motion.div>
  );
};

export default ResumeComparePage;

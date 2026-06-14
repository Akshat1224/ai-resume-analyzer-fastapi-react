import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";

const ResumeAnalyzerPage=()=> {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

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

  const connectToProgressStream = () => {
    const eventSource = new EventSource("http://localhost:8000/resume/stream");
    eventSource.onmessage = (event) => {
      setProgress(event.data);
      if (event.data === "Completed") {
        eventSource.close();
      }
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
      connectToProgressStream();

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/resume/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to analyze resume. Please try again.");
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

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col h-full w-full gap-2 p-2"
    >
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex rounded-3xl border border-white/10 bg-slate-950/80 p-8 h-full w-full shadow-2xl shadow-cyan-500/10 backdrop-blur-xl"
      >
        <div className="grid grid-cols-2 gap-2">
          <div className="w-full flex flex-col gap-2">
            <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 shadow-sm shadow-cyan-500/10">
              <span className="text-base">✨</span>
              <span>Resume analysis made fast, clear, and actionable.</span>
            </div>
            <div className="flex flex-col gap-2">
              <h1 className="text-4xl font-semibold tracking-tight text-white ">
                Smart resume review with instant AI feedback.
              </h1>
              <p className="mt-4 max-w-2xl text-slate-300 sm:text-lg">
                Upload your PDF and get a sharp summary of strengths,
                weaknesses, missing skills, and ATS readiness—all with a
                polished experience.
              </p>
            </div>
          </div>

          <div className="grid gap-3 grid-cols-3">
            {[
              { label: "Fast feedback", value: "< 20s" },
              { label: "PDF support", value: "Single page" },
              { label: "AI-ready", value: "JSON output" },
            ].map((item) => (
              <motion.div
                key={item.label}
                whileHover={{ y: -4 }}
                className="rounded-3xl border border-white/10 bg-slate-900/80 p-2 text-center shadow-lg flex flex-col gap-2 items-center justify-center shadow-slate-950/20"
              >
                <p className="text-sm uppercase tracking-[0.18em] text-slate-400">
                  {item.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {item.value}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="grid gap-2 grid-cols-2"
      >
        <div className="flex flex-col h-full w-full gap-4 ">
          <motion.div
            layout
            className="rounded-3xl border border-white/10 bg-slate-950/80 p-4 shadow-2xl shadow-slate-950/10 backdrop-blur-xl flex flex-col gap-2"
          >
            <h2 className="text-2xl font-semibold text-white">Upload resume</h2>
            <p className=" text-slate-400">
              Drag & drop your PDF or click the box below. Then hit analyze to
              begin the AI review.
            </p>

            <div
              {...getRootProps()}
              className={` border-2 rounded-4xl p-2  flex flex-col items-center justify-center gap-4 text-center transition-all duration-300 ${
                isDragActive
                  ? "border-blue-400 bg-slate-900/90 shadow-[0_18px_60px_-42px_rgba(59,130,246,0.8)]"
                  : "border-slate-700 bg-slate-950/40"
              } cursor-pointer hover:border-cyan-400`}
            >
              <input {...getInputProps()} />
              <span className="text-5xl">📤</span>
              <div>
                <p className="text-xl font-semibold text-white">
                  {file ? file.name : "Drag & drop your PDF resume"}
                </p>
                <p className="mt-2 text-sm text-slate-400">
                  {file
                    ? "File selected: ready to analyze"
                    : "PDF only — drop it or click to choose"}
                </p>
              </div>
              <p className="text-xs text-slate-500">
                {isDragActive
                  ? "Drop to upload"
                  : "Single-page PDF recommended"}
              </p>
            </div>

            <button
              onClick={handleUpload}
              disabled={loading || !file}
              className={` w-full rounded-3xl p-4 text-sm font-semibold uppercase tracking-[0.18em] transition duration-300 ${
                loading || !file
                  ? "cursor-not-allowed bg-slate-700 text-slate-400"
                  : "bg-linear-to-r from-cyan-500 to-blue-500 text-white shadow-xl shadow-cyan-500/20 hover:brightness-110"
              }`}
            >
              {loading ? (
                <div className="flex items-center justify-center gap-3">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                  Analyzing resume...
                </div>
              ) : (
                "Analyze resume"
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
                className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-slate-950/10"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.2em] text-slate-400">
                      Processing
                    </p>
                    <p className="mt-2 text-base text-white">{progress}</p>
                  </div>
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-300">
                    ⏳
                  </span>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
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

        <motion.div
          layout
          className="flex flex-col gap-2 rounded-3xl border border-white/10 bg-slate-950/80 p-4 shadow-2xl shadow-slate-950/10 backdrop-blur-xl"
        >
          <h2 className="text-2xl font-semibold text-white">Quick notes</h2>
          <div className=" grid gap-4">
            {[
              "Faster feedback with streaming updates",
              "Auto-detect strengths and weaknesses",
              "Clean PDF input, no manual copy/paste",
            ].map((note) => (
              <motion.div
                key={note}
                whileHover={{ x: 4 }}
                className="rounded-3xl border border-slate-700/80 bg-slate-900/70 p-4 text-sm text-slate-300"
              >
                {note}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </motion.section>

      <AnimatePresence>
        {error && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="rounded-3xl border border-red-500/10 bg-red-950/70 p-6 text-white shadow-lg shadow-red-500/10"
          >
            <p className="font-semibold text-red-300">Error</p>
            <p className="mt-2 text-slate-200">{error}</p>
          </motion.section>
        )}
      </AnimatePresence>

      {result && (
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="space-y-6"
        >
          <motion.div
            layout
            className="rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-slate-950/10 backdrop-blur-xl"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-cyan-300/80">
                  AI analysis complete
                </p>
                <h2 className="mt-2 text-3xl font-semibold text-white">
                  Resume insights
                </h2>
              </div>
              <div className="rounded-3xl bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
                {result.ats_score != null
                  ? `ATS score ${result.ats_score}`
                  : "Awaiting model response"}
              </div>
            </div>
          </motion.div>

          {result.error ? (
            <motion.div
              layout
              className="rounded-3xl border border-red-500/10 bg-red-950/70 p-6 text-red-200"
            >
              <p className="font-semibold">{result.error}</p>
              {result.details && (
                <p className="mt-2 text-sm">{result.details}</p>
              )}
            </motion.div>
          ) : (
            <div className="grid gap-6">
              <motion.div
                layout
                className={`${getScoreBgColor(result.ats_score)} rounded-3xl border p-8 text-center shadow-xl shadow-slate-950/20`}
              >
                <p className="text-sm uppercase tracking-[0.2em] text-slate-300">
                  ATS Score
                </p>
                <p
                  className={`mt-4 text-6xl font-bold ${getScoreColor(result.ats_score)}`}
                >
                  {result.ats_score}
                </p>
                <p className="mt-3 text-slate-300">
                  {result.ats_score >= 80
                    ? "Excellent — this resume is ATS-friendly"
                    : result.ats_score >= 60
                      ? "Good — a few improvements will help"
                      : "Needs improvement for better ATS success"}
                </p>
              </motion.div>

              <div className="grid gap-6 xl:grid-cols-2">
                {result.strengths && result.strengths.length > 0 && (
                  <motion.div
                    layout
                    className="rounded-3xl border border-slate-700/80 bg-slate-900/80 p-6"
                  >
                    <div className="mb-4 flex items-center gap-3">
                      <span className="text-2xl">✅</span>
                      <h3 className="text-xl font-semibold text-white">
                        Strengths
                      </h3>
                    </div>
                    <ul className="space-y-3 text-slate-300">
                      {result.strengths.map((item, index) => (
                        <li key={index} className="flex gap-3">
                          <span className="text-cyan-400">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}

                {result.weaknesses && result.weaknesses.length > 0 && (
                  <motion.div
                    layout
                    className="rounded-3xl border border-slate-700/80 bg-slate-900/80 p-6"
                  >
                    <div className="mb-4 flex items-center gap-3">
                      <span className="text-2xl">⚠️</span>
                      <h3 className="text-xl font-semibold text-white">
                        Weaknesses
                      </h3>
                    </div>
                    <ul className="space-y-3 text-slate-300">
                      {result.weaknesses.map((item, index) => (
                        <li key={index} className="flex gap-3">
                          <span className="text-yellow-400">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}
              </div>

              {result.missing_skills && result.missing_skills.length > 0 && (
                <motion.div
                  layout
                  className="rounded-3xl border border-slate-700/80 bg-slate-900/80 p-6"
                >
                  <div className="mb-4 flex items-center gap-3">
                    <span className="text-2xl">🎯</span>
                    <h3 className="text-xl font-semibold text-white">
                      Missing Skills
                    </h3>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {result.missing_skills.map((item, index) => (
                      <div
                        key={index}
                        className="rounded-3xl bg-slate-950/60 px-4 py-3 text-slate-300"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {result.suggestions && result.suggestions.length > 0 && (
                <motion.div
                  layout
                  className="rounded-3xl border border-slate-700/80 bg-slate-900/80 p-6"
                >
                  <div className="mb-4 flex items-center gap-3">
                    <span className="text-2xl">💡</span>
                    <h3 className="text-xl font-semibold text-white">
                      Suggestions
                    </h3>
                  </div>
                  <ul className="space-y-3 text-slate-300">
                    {result.suggestions.map((item, index) => (
                      <li key={index} className="flex gap-3">
                        <span className="text-blue-400">→</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}
            </div>
          )}
        </motion.section>
      )}
    </motion.div>
  );
}

export default ResumeAnalyzerPage;

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import FullScreenSpinner from "../components/reusable/FullScreenSpinner";
import Dropdown from "../components/reusable/Dropdown";

export default function Interview() {
  const [role, setRole] = useState("");
  const [industry, setIndustry] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("mid");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(5);
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState("");
  const [expandedIndex, setExpandedIndex] = useState(null);

  const roles = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Product Manager",
    "UI/UX Designer",
    "DevOps Engineer",
    "Mobile Developer",
    "QA Engineer",
  ];

  const industries = [
    "Technology",
    "Finance",
    "Healthcare",
    "E-commerce",
    "Education",
    "Media & Entertainment",
    "Manufacturing",
    "Retail",
    "Automotive",
    "Consulting",
  ];

  const difficulties = [
    { value: "easy", label: "Easy - Basics & theory" },
    { value: "medium", label: "Medium - Practical experience" },
    { value: "hard", label: "Hard - Advanced & complex" },
  ];

  const mutation = useMutation({
    mutationFn: async (payload) => {
      const response = await fetch("http://localhost:8000/interview/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || "Failed to generate questions");
      }

      return response.json();
    },
    onSuccess: (data) => {
      setQuestions(data.questions || []);
    },
    onError: () => {
      setError("Failed to generate questions. Please try again.");
    },
  });

  const generateQuestions = useCallback(() => {
    if (!role || !industry || !experienceLevel) {
      setError("Please select a role, industry and experience level");
      return;
    }

    setError("");
    setQuestions([]);

    mutation.mutate({
      role,
      industry,
      experience_level: experienceLevel,
      difficulty,
      num_questions: numQuestions,
    });
  }, [difficulty, experienceLevel, industry, numQuestions, role, mutation]);

  return (
    <div className="flex-1 overflow-auto space-y-4 p-2">
      {mutation.isPending && <FullScreenSpinner />}

      {/* Header */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col gap-2"
      >
        <div>
          <h1 className="text-4xl font-bold text-white">Interview Prep</h1>
          <p className=" text-slate-400">
            Generate personalized interview questions to practice and ace your
            next interview.
          </p>
        </div>
      </motion.section>

      {/* Parameters Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex flex-col gap-2 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-xl backdrop-blur-xl"
      >
        <h2 className="text-2xl font-semibold text-white">
          Question Parameters
        </h2>

        <div className="grid gap-6 grid-cols-2">
          {/* Role Selection  */}
          <Dropdown
            label="Job Role"
            value={role}
            onChange={setRole}
            options={roles}
            placeholder="Select a role..."
            searchable
          />

          {/* Industry Selection  */}
          <Dropdown
            label="Industry"
            value={industry}
            onChange={setIndustry}
            options={industries}
            placeholder="Select an industry..."
            searchable
          />

          {/* Difficulty Selection */}
          <motion.div layout className="space-y-3">
            <label className="block text-sm font-medium text-slate-300">
              Difficulty Level
            </label>
            <div className="grid gap-2 sm:grid-cols-3">
              {difficulties.map((d) => (
                <motion.button
                  key={d.value}
                  whileHover={{ scale: 1.02 }}
                  onClick={() => setDifficulty(d.value)}
                  className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${
                    difficulty === d.value
                      ? "border-cyan-400 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 bg-slate-900/50 text-slate-400 hover:text-white"
                  }`}
                >
                  {d.label}
                </motion.button>
              ))}
            </div>
          </motion.div>

          {/* Experience Level Selection */}
          <motion.div layout className="space-y-3">
            <label className="block text-sm font-medium text-slate-300">
              Experience Level
            </label>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {[
                { value: "junior", label: "Junior" },
                { value: "mid", label: "Mid" },
                { value: "senior", label: "Senior" },
              ].map((lvl) => (
                <button
                  key={lvl.value}
                  onClick={() => setExperienceLevel(lvl.value)}
                  className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${
                    experienceLevel === lvl.value
                      ? "border-cyan-400 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 bg-slate-900/50 text-slate-400 hover:text-white"
                  }`}
                >
                  {lvl.label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Number of Questions */}
          <motion.div layout className="space-y-3">
            <label className="block text-sm font-medium text-slate-300">
              Number of Questions: {numQuestions}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={numQuestions}
              onChange={(e) => setNumQuestions(parseInt(e.target.value))}
              className="w-full"
            />
          </motion.div>
        </div>

        {/* Generate Button */}
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={generateQuestions}
          disabled={
            mutation.isPending || !role || !industry || !experienceLevel
          }
          className={`mt-8 w-full rounded-2xl px-6 py-4 font-semibold uppercase tracking-[0.18em] transition ${
            mutation.isPending || !role || !industry || !experienceLevel
              ? "cursor-not-allowed bg-slate-700 text-slate-400"
              : "bg-linear-to-r from-cyan-500 to-blue-500 text-white shadow-xl shadow-cyan-500/20 hover:brightness-110"
          }`}
        >
          {mutation.isPending ? (
            <div className="flex items-center justify-center gap-3">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              Generating Questions...
            </div>
          ) : (
            "Generate Interview Questions"
          )}
        </motion.button>
      </motion.section>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="rounded-2xl border border-red-500/30 bg-red-950/50 p-4 text-red-200"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Questions Display */}
      <AnimatePresence>
        {questions.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-4">
              <p className="text-sm text-slate-400">
                Generated {questions.length} interview questions for{" "}
                <span className="font-semibold text-cyan-300">{role}</span> in{" "}
                <span className="font-semibold text-cyan-300">{industry}</span>
              </p>
            </div>

            <div className="space-y-3">
              {questions.map((q, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="rounded-2xl border border-white/10 bg-slate-950/80 p-6 backdrop-blur-sm"
                >
                  <motion.button
                    onClick={() =>
                      setExpandedIndex(expandedIndex === index ? null : index)
                    }
                    whileHover={{ x: 2 }}
                    className="w-full text-left"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-cyan-400">
                          Question {index + 1}
                        </p>
                        <p className="mt-2 font-medium text-white">
                          {q.question}
                        </p>
                      </div>
                      <span className="mt-1 shrink-0 text-lg text-slate-400">
                        {expandedIndex === index ? "▼" : "▶"}
                      </span>
                    </div>
                  </motion.button>

                  <AnimatePresence>
                    {expandedIndex === index && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="mt-4 border-t border-slate-700/50 pt-4"
                      >
                        <div className="space-y-3">
                          {q.hints && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                                💡 Hints
                              </p>
                              <p className="mt-1 text-sm text-slate-300">
                                {q.hints}
                              </p>
                            </div>
                          )}
                          {q.sample_answer && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                                ✓ Sample Answer
                              </p>
                              <p className="mt-1 text-sm text-slate-300">
                                {q.sample_answer}
                              </p>
                            </div>
                          )}
                          {q.difficulty && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                                Difficulty:
                              </span>
                              <span
                                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                  q.difficulty === "easy"
                                    ? "bg-green-500/20 text-green-300"
                                    : q.difficulty === "medium"
                                      ? "bg-yellow-500/20 text-yellow-300"
                                      : "bg-red-500/20 text-red-300"
                                }`}
                              >
                                {q.difficulty}
                              </span>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}

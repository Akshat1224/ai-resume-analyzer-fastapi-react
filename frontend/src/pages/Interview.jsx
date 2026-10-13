import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import FullScreenSpinner from "../components/reusable/FullScreenSpinner";
import Dropdown from "../components/reusable/Dropdown";
import { config } from "../config";

export default function Interview() {
  const location = useLocation();
  const [role, setRole] = useState("");
  const [industry, setIndustry] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("mid");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(5);
  const [skillGaps, setSkillGaps] = useState("");
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState("");
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [practiceMode, setPracticeMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [sessionId] = useState(() => "interview_" + Date.now());
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (location.state?.skillGaps) {
      setSkillGaps(location.state.skillGaps);
    }
  }, [location.state]);

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
      setIsGenerating(true);
      try {
        const response = await fetch(`${config.apiUrl}/interview/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const body = await response.text();
          throw new Error(body || "Failed to generate questions");
        }

        return response.json();
      } finally {
        setIsGenerating(false);
      }
    },
    onSuccess: (data) => {
      setQuestions(data.questions || []);
      setPracticeMode(true);
      setCurrentQuestionIndex(0);
      setUserAnswer("");
      setFeedback(null);
    },
    onError: (error) => {
      setError(error.message || "Failed to generate questions. Please try again.");
    },
  });

  const practiceMutation = useMutation({
    mutationFn: async (payload) => {
      setIsSubmitting(true);
      try {
        const response = await fetch(`${config.apiUrl}/interview/attempt`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const body = await response.text();
          throw new Error(body || "Failed to submit answer");
        }

        const data = await response.json();

        // Add minimal delay for UX - ensures loading spinner is visible
        await new Promise(resolve => setTimeout(resolve, 800));

        return data;
      } finally {
        setIsSubmitting(false);
      }
    },
    onSuccess: (data) => {
      setFeedback(data);
    },
    onError: (error) => {
      setError(error.message || "Failed to submit answer. Please try again.");
    },
  });

  const { data: progressData, isLoading: progressLoading } = useQuery({
    queryKey: ["interview-progress", sessionId],
    queryFn: async () => {
      const response = await fetch(`${config.apiUrl}/interview/progress?session_id=${sessionId}`);
      if (!response.ok) throw new Error("Failed to fetch progress");
      return response.json();
    },
    enabled: practiceMode,
  });

  const generateQuestions = useCallback(() => {
    if (!role || !industry || !experienceLevel) {
      setError("Please select a role, industry and experience level");
      return;
    }

    setError("");
    setQuestions([]);

    const payload = {
      role,
      industry,
      experience_level: experienceLevel,
      difficulty,
      num_questions: numQuestions,
      session_id: sessionId,
    };

    if (skillGaps.trim()) {
      payload.skill_gaps = skillGaps.split(",").map(s => s.trim()).filter(s => s);
    }

    mutation.mutate(payload);
  }, [difficulty, experienceLevel, industry, numQuestions, role, mutation, skillGaps, sessionId]);

  const submitAnswer = useCallback(() => {
    if (!userAnswer.trim()) {
      setError("Please provide an answer");
      return;
    }

    const currentQ = questions[currentQuestionIndex];
    practiceMutation.mutate({
      question: currentQ.question,
      target_skill: currentQ.target_skill || role,
      difficulty: currentQ.difficulty || difficulty,
      user_answer: userAnswer,
      session_id: sessionId,
    });
  }, [currentQuestionIndex, questions, userAnswer, difficulty, role, sessionId, practiceMutation]);

  const nextQuestion = useCallback(() => {
    setFeedback(null);
    setUserAnswer("");
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      setPracticeMode(false);
    }
  }, [currentQuestionIndex, questions.length]);

  return (
    <div className="flex-1 overflow-auto space-y-4 p-2">
      {(isGenerating || isSubmitting) && <FullScreenSpinner />}

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

          {/* Skill Gaps (Optional) */}
          <motion.div layout className="space-y-3 col-span-2">
            <label className="block text-sm font-medium text-slate-300">
              Target Skill Gaps (Optional)
            </label>
            <input
              type="text"
              value={skillGaps}
              onChange={(e) => setSkillGaps(e.target.value)}
              placeholder="e.g., Kubernetes, Docker, AWS (comma-separated)"
              className="w-full rounded-xl border border-slate-700 bg-slate-900/50 px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
            <p className="text-xs text-slate-400">
              If you've identified skill gaps from resume analysis, enter them here for targeted practice questions.
            </p>
          </motion.div>
        </div>

        {/* Generate Button */}
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={generateQuestions}
          disabled={
            isGenerating || !role || !industry || !experienceLevel
          }
          className={`mt-8 w-full rounded-2xl px-6 py-4 font-semibold uppercase tracking-[0.18em] transition ${
            isGenerating || !role || !industry || !experienceLevel
              ? "cursor-not-allowed bg-slate-700 text-slate-400"
              : "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-xl shadow-cyan-500/20 hover:brightness-110"
          }`}
        >
          {isGenerating ? (
            <div className="flex items-center justify-center gap-3">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              Generating Questions...
            </div>
          ) : (
            "Generate Interview Questions"
          )}
        </motion.button>
      </motion.section>

      {/* Practice Mode */}
      <AnimatePresence>
        {practiceMode && !progressLoading && progressData && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-xl backdrop-blur-xl"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-white">Your Progress</h3>
              <span className="text-sm text-slate-400">
                Total Attempts: {progressData.total_attempts}
              </span>
            </div>
            {progressData.recommended_focus.length > 0 && (
              <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-950/20 p-3">
                <p className="text-xs font-semibold text-amber-300 mb-2">Recommended Focus Areas:</p>
                <div className="flex flex-wrap gap-2">
                  {progressData.recommended_focus.map((skill, idx) => (
                    <span key={idx} className="px-2 py-1 rounded-full bg-amber-500/10 text-amber-300 text-xs">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {progressData.skills_tracked.length > 0 && (
              <div className="space-y-2">
                {progressData.skills_tracked.map((skill, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                    <div>
                      <p className="text-sm font-medium text-white">{skill.skill}</p>
                      <p className="text-xs text-slate-400">
                        {skill.attempts_count} attempts • Avg: {skill.average_score}%
                      </p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      skill.mastery_status === "mastered" ? "bg-emerald-500/20 text-emerald-300" :
                      skill.mastery_status === "proficient" ? "bg-blue-500/20 text-blue-300" :
                      "bg-rose-500/20 text-rose-300"
                    }`}>
                      {skill.mastery_status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </motion.section>
        )}
      </AnimatePresence>

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

      {/* Practice Mode - Answer Questions */}
      <AnimatePresence>
        {practiceMode && questions.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.5 }}
            className="space-y-4"
          >
            <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-4">
              <p className="text-sm text-slate-400">
                Question {currentQuestionIndex + 1} of {questions.length}
              </p>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-2xl border border-white/10 bg-slate-950/80 p-6 backdrop-blur-sm"
            >
              <div className="mb-4">
                <p className="text-sm font-medium text-cyan-400 mb-2">
                  {questions[currentQuestionIndex].target_skill || role}
                </p>
                <p className="text-lg font-medium text-white">
                  {questions[currentQuestionIndex].question}
                </p>
              </div>

              {!feedback ? (
                <div className="space-y-4">
                  <textarea
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Type your answer here... (Use STAR method: Situation, Task, Action, Result)"
                    rows={6}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/50 p-4 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none resize-none"
                  />
                  <div className="flex gap-3">
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={submitAnswer}
                      disabled={isSubmitting || !userAnswer.trim()}
                      className={`flex-1 rounded-xl px-6 py-3 font-semibold uppercase tracking-[0.14em] transition ${
                        isSubmitting || !userAnswer.trim()
                          ? "cursor-not-allowed bg-slate-700 text-slate-400"
                          : "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20 hover:brightness-110"
                      }`}
                    >
                      {isSubmitting ? "Submitting..." : "Submit Answer"}
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => {
                        setFeedback(null);
                        setUserAnswer("");
                      }}
                      className="rounded-xl px-6 py-3 font-semibold text-slate-400 border border-slate-700 hover:bg-slate-800 transition"
                    >
                      Skip
                    </motion.button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className={`rounded-xl p-4 ${
                    feedback.score >= 70 ? "bg-emerald-950/30 border border-emerald-500/20" :
                    feedback.score >= 50 ? "bg-amber-950/30 border border-amber-500/20" :
                    "bg-red-950/30 border border-red-500/20"
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-semibold text-white">Score: {feedback.score}/100</p>
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        feedback.score >= 70 ? "bg-emerald-500/20 text-emerald-300" :
                        feedback.score >= 50 ? "bg-amber-500/20 text-amber-300" :
                        "bg-red-500/20 text-red-300"
                      }`}>
                        {feedback.score >= 70 ? "Good" : feedback.score >= 50 ? "Fair" : "Needs Work"}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300">{feedback.feedback}</p>
                  </div>

                  {feedback.suggested_improvements.length > 0 && (
                    <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                      <p className="text-xs font-semibold text-slate-400 mb-2">Suggested Improvements:</p>
                      <ul className="space-y-1">
                        {feedback.suggested_improvements.map((improvement, idx) => (
                          <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                            <span className="text-cyan-400">•</span>
                            {improvement}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={nextQuestion}
                      className="flex-1 rounded-xl px-6 py-3 font-semibold bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20 hover:brightness-110 transition"
                    >
                      {currentQuestionIndex < questions.length - 1 ? "Next Question" : "Finish Practice"}
                    </motion.button>
                  </div>
                </div>
              )}
            </motion.div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}

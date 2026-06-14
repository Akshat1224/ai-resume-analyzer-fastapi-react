import { motion } from "framer-motion";

export default function About() {
  const features = [
    {
      icon: "📄",
      title: "Resume Analyzer",
      description:
        "Get AI-powered feedback on your resume. Analyze ATS compatibility, strengths, weaknesses, and get actionable improvement suggestions.",
    },
    {
      icon: "🎯",
      title: "Interview Prep",
      description:
        "Generate realistic interview questions tailored to specific roles, industries, and difficulty levels. Practice your answers with AI feedback.",
    },
    {
      icon: "⚡",
      title: "Lightning Fast",
      description:
        "Powered by local LLM streaming. Get instant feedback without waiting, with real-time response streaming.",
    },
  ];

  const stats = [
    { value: "< 20s", label: "Analysis Time" },
    { value: "Real-time", label: "Streaming" },
    { value: "100%", label: "Local Processing" },
  ];
  const techStats = [
    { name: "React 19", desc: "Modern UI" },
    { name: "Framer Motion", desc: "Smooth animations" },
    { name: "FastAPI", desc: "Fast backend" },
    { name: "Local LLM", desc: "Ollama powered" },
  ];

  return (
    <div className="flex-1 overflow-auto space-y-4  p-4">
      {/* Hero Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl backdrop-blur-xl"
      >
        <div className="flex flex-col gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-white ">
            Your AI Career Assistant
          </h1>
          <p className="max-w-2xl text-xl text-slate-300">
            Ace interviews and optimize your resume with intelligent, real-time
            AI feedback powered by local LLM technology.
          </p>
        </div>

        <div className="grid gap-4 grid-cols-3">
          {stats.map((stat) => (
            <motion.div
              key={stat.label}
              whileHover={{ y: -4 }}
              className="rounded-2xl border border-white/10 bg-slate-900/50 p-4 text-center flex flex-col gap-2"
            >
              <p className="text-2xl font-bold text-cyan-400">{stat.value}</p>
              <p className="text-sm text-slate-400">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* Features Section */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="flex flex-col gap-3"
      >
        <div className="flex flex-col gap-2 text-center">
          <h2 className="text-3xl font-bold text-slate-600">What You Can Do</h2>
          <p className=" text-slate-400">
            Everything you need to ace your career
          </p>
        </div>

        <div className="grid gap-4 grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 * (index + 1) }}
              whileHover={{ y: -8 }}
              className="rounded-2xl border border-white/10 bg-slate-950/80 p-6 shadow-lg backdrop-blur-sm flex flex-col gap-2"
            >
              <span className="text-4xl">{feature.icon}</span>
              <h3 className=" text-xl font-semibold text-white">
                {feature.title}
              </h3>
              <p className=" text-slate-400">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* Tech Stack */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 backdrop-blur-xl flex flex-col space-y-4"
      >
        <h2 className="text-3xl font-bold text-white">Technology</h2>
        <div className="grid gap-6 grid-cols-4">
          {techStats.map((tech) => (
            <div
              key={tech.name}
              className="rounded-xl border border-slate-700/50 bg-slate-900/50 p-4 flex flex-col gap-2"
            >
              <p className="font-semibold text-cyan-400">{tech.name}</p>
              <p className=" text-sm text-slate-400">{tech.desc}</p>
            </div>
          ))}
        </div>
      </motion.section>

      {/* CTA */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="rounded-3xl border border-cyan-400/30 bg-linear-to-r from-cyan-500/40 to-blue-500/10 p-6 text-center backdrop-blur-sm flex flex-col gap-2"
      >
        <h2 className="text-2xl font-bold text-slate-600">Ready to get started?</h2>
        <p className=" text-slate-500">
          Use the Resume Analyzer or Interview Prep tools above to begin.
        </p>
      </motion.section>
    </div>
  );
}

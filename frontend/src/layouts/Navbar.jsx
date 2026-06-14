import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";

export default function Navbar() {
  const location = useLocation();

  const tabs = [
    { label: "About", path: "/", icon: "ℹ️" },
    { label: "Resume Analyzer", path: "/resume", icon: "📄" },
    { label: "Interview", path: "/interview", icon: "🎯" },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl">
      <div className="grid grid-cols-3 gap-2 p-4 items-center mx-auto">
        {/* Logo/Brand */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-2"
        >
          <span className="text-2xl">✨</span>
          <span className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            AI Assistant
          </span>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 w-full p-2 rounded-full border border-white/10 bg-slate-900/50 ">
          {tabs.map((tab) => {
            const isActive = location.pathname === tab.path;
            return (
              <Link key={tab.path} to={tab.path} className="relative">
                <motion.div
                  whileHover={{ y: -2 }}
                  className={`flex items-center gap-2 w-full rounded-full px-4 py-2 text-sm font-medium transition ${
                    isActive ? "text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 rounded-full bg-linear-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-400/30"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.3 }}
                    />
                  )}
                  <span className="relative z-10">{tab.icon}</span>
                  <span className="relative z-10">{tab.label}</span>
                </motion.div>
              </Link>
            );
          })}
        </div>
        <div></div>
      </div>
    </nav>
  );
}

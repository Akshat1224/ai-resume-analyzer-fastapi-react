export default function FullScreenSpinner({
  message = "Generating interview questions...",
}) {
  return (
    <div
      className="fixed inset-0 flex items-center justify-center bg-slate-950/90 p-4 animate-[fadeIn_0.2s_ease-out]"
      style={{ zIndex: 9999 }}
    >
      <div className="flex max-w-md flex-col items-center rounded-3xl border border-cyan-500/20 bg-slate-900/95 px-8 py-10 text-center shadow-2xl shadow-cyan-500/10">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border-4 border-cyan-500/20 border-t-cyan-400 animate-spin" />
        <p className="text-lg font-semibold text-white">{message}</p>
        <p className="mt-2 max-w-sm text-sm text-slate-400">
          Please wait while the questions are being generated. This may take a
          few seconds.
        </p>
      </div>
    </div>
  );
}
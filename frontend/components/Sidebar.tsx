"use client";

import { useWizardStore } from "@/lib/store";

export default function Sidebar() {
  const resetWizard = useWizardStore((s) => s.resetWizard);

  return (
    <aside className="sticky top-8 flex h-fit flex-col gap-4 rounded-2xl border border-slate-200 bg-white/80 p-5 text-sm shadow-md dark:border-slate-800 dark:bg-slate-900/70">
      <div className="rounded-xl bg-gradient-to-r from-amber-300 to-amber-400 px-4 py-2 text-center font-semibold text-amber-900 shadow">
        9th Mirae Asset Securities AI Festival
      </div>

      <div>
        <h5 className="mb-1 font-semibold text-slate-700 dark:text-slate-200">About</h5>
        <p className="text-slate-500 dark:text-slate-400">
          AI-powered portfolio construction combining a machine-learning ensemble, live FRED economic
          data, and news-sentiment filtering, tailored to your risk profile and industry preferences.
        </p>
      </div>

      <div>
        <h5 className="mb-1 font-semibold text-slate-700 dark:text-slate-200">Disclaimer</h5>
        <p className="text-slate-500 dark:text-slate-400">
          Educational project only. Always consult a qualified financial advisor before making
          investment decisions.
        </p>
      </div>

      <button
        onClick={resetWizard}
        className="mt-2 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 px-4 py-2 text-center font-medium text-white shadow transition-transform hover:-translate-y-0.5"
      >
        Reset progress
      </button>
    </aside>
  );
}

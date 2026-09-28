"use client";

import Link from "next/link";
import InfoCard from "@/components/InfoCard";
import MetricCard from "@/components/MetricCard";

export default function WelcomePage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="text-center">
        <h1 className="bg-brand-gradient bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
          Finvizor Pro
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Built for the 9th Mirae Asset Securities AI Festival
        </p>
      </div>

      <div className="rounded-2xl border border-amber-300/60 bg-amber-50 px-6 py-4 text-center text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        This is an educational project. Always consult a qualified financial advisor before making
        investment decisions.
      </div>

      <InfoCard className="text-center">
        <h2 className="mb-2 text-2xl font-semibold">Next-Generation AI Portfolio Management</h2>
        <p className="text-slate-500 dark:text-slate-400">
          Machine-learning return prediction, live FRED economic data, and news-sentiment filtering,
          combined into a personalized portfolio tailored to your risk profile and industry focus.
        </p>
      </InfoCard>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <InfoCard title="AI-Powered Analysis">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            <li>RandomForest + GradientBoosting + XGBoost ensemble</li>
            <li>Per-symbol ARIMA return forecasting</li>
            <li>21 FRED economic indicators</li>
            <li>Multi-method news sentiment risk filtering</li>
          </ul>
        </InfoCard>
        <InfoCard title="Personalized Portfolios">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            <li>Industry focus customization</li>
            <li>Risk-tolerance driven filtering</li>
            <li>AI-optimized or fully manual construction</li>
            <li>Real-time progress while the model trains</li>
          </ul>
        </InfoCard>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard value="60+" label="US Stocks Analyzed" />
        <MetricCard value="21" label="Economic Indicators" />
        <MetricCard value="3" label="ML Models" />
        <MetricCard value="Real-Time" label="Market Data" />
      </div>

      <div className="flex justify-center">
        <Link
          href="/industry-focus"
          className="rounded-full bg-brand-gradient-soft px-8 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30 transition-transform hover:-translate-y-0.5"
        >
          Get Started with Industry Focus →
        </Link>
      </div>
    </div>
  );
}

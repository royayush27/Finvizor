"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, pollJobUntilDone } from "@/lib/api";
import { useWizardStore } from "@/lib/store";
import type { ManualHolding, NewsRiskTolerance, PortfolioMode } from "@/lib/types";
import InfoCard from "@/components/InfoCard";

// Mirrors backend/app/services/stock_universe.py::MANUAL_SELECT_SYMBOLS
const MANUAL_SELECT_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "V", "PG", "JNJ",
  "UNH", "HD", "MA", "BAC", "KO", "PEP", "DIS", "NFLX", "ADBE", "CRM",
];

const NEWS_RISK_OPTIONS: NewsRiskTolerance[] = ["CONSERVATIVE", "MEDIUM", "AGGRESSIVE"];

export default function PortfolioBuilderPage() {
  const router = useRouter();
  const industryFocus = useWizardStore((s) => s.industryFocus);
  const excludeIndustries = useWizardStore((s) => s.excludeIndustries);
  const esgPreference = useWizardStore((s) => s.esgPreference);
  const questionnaire = useWizardStore((s) => s.questionnaire);
  const riskScore = useWizardStore((s) => s.riskScore);
  const setActiveJob = useWizardStore((s) => s.setActiveJob);
  const setPortfolio = useWizardStore((s) => s.setPortfolio);

  const [mode, setMode] = useState<PortfolioMode>("ai_optimized");
  const [numStocks, setNumStocks] = useState(10);
  const [newsRiskTolerance, setNewsRiskTolerance] = useState<NewsRiskTolerance>("MEDIUM");
  const [manualSelection, setManualSelection] = useState<Record<string, number>>({});

  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const manualTotalWeight = Object.values(manualSelection).reduce((sum, w) => sum + w, 0);

  function toggleManualSymbol(symbol: string) {
    setManualSelection((prev) => {
      const next = { ...prev };
      if (symbol in next) {
        delete next[symbol];
      } else {
        next[symbol] = 0;
      }
      return next;
    });
  }

  async function handleGenerate() {
    if (riskScore === null) {
      setError("Please complete the risk assessment step first.");
      return;
    }

    let manualHoldings: ManualHolding[] | undefined;
    if (mode === "user_defined") {
      const symbols = Object.keys(manualSelection);
      if (symbols.length === 0) {
        setError("Select at least one stock.");
        return;
      }
      if (Math.abs(manualTotalWeight - 100) > 0.5) {
        setError("Weights must sum to 100%.");
        return;
      }
      manualHoldings = symbols.map((symbol) => ({ symbol, weight: manualSelection[symbol] / 100 }));
    }

    setGenerating(true);
    setError(null);
    setProgress(0);
    setProgressMessage("Starting...");

    try {
      const job = await api.generatePortfolio({
        mode,
        industry_focus: industryFocus,
        exclude_industries: excludeIndustries,
        esg_preference: esgPreference,
        questionnaire,
        risk_score: riskScore,
        news_risk_tolerance: newsRiskTolerance,
        num_stocks: numStocks,
        manual_holdings: manualHoldings,
      });

      const finalJob = await pollJobUntilDone(job.job_id, (update) => {
        setActiveJob(update);
        setProgress(update.progress);
        setProgressMessage(update.message ?? "");
      });

      if (finalJob.status === "completed" && finalJob.result) {
        setPortfolio(finalJob.result);
        router.push("/results");
      } else {
        setError(finalJob.error ?? "Portfolio generation failed.");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the backend. Is it running?");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold">Portfolio Builder</h1>
        <p className="text-slate-500 dark:text-slate-400">
          Let the AI build a portfolio for you, or pick your own holdings.
        </p>
      </div>

      <div className="flex gap-2">
        {(["ai_optimized", "user_defined"] as PortfolioMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
              mode === m
                ? "border-transparent bg-brand-gradient-soft text-white shadow-lg shadow-indigo-500/30"
                : "border-slate-200 dark:border-slate-800"
            }`}
          >
            {m === "ai_optimized" ? "AI-Optimized Portfolio" : "User-Defined Portfolio"}
          </button>
        ))}
      </div>

      {mode === "ai_optimized" ? (
        <InfoCard title="AI-Optimized Settings">
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold">Number of stocks: {numStocks}</span>
              <input
                type="range"
                min={3}
                max={20}
                value={numStocks}
                onChange={(e) => setNumStocks(Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold">News risk tolerance</span>
              <select
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                value={newsRiskTolerance}
                onChange={(e) => setNewsRiskTolerance(e.target.value as NewsRiskTolerance)}
              >
                {NEWS_RISK_OPTIONS.map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
          </div>
        </InfoCard>
      ) : (
        <InfoCard title="Select holdings and weights (must sum to 100%)">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {MANUAL_SELECT_SYMBOLS.map((symbol) => (
              <button
                key={symbol}
                onClick={() => toggleManualSymbol(symbol)}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  symbol in manualSelection
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                    : "border-slate-200 dark:border-slate-800"
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>

          {Object.keys(manualSelection).length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              {Object.keys(manualSelection).map((symbol) => (
                <label key={symbol} className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{symbol}</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    className="w-24 rounded-lg border border-slate-300 bg-white px-2 py-1 text-right dark:border-slate-700 dark:bg-slate-900"
                    value={manualSelection[symbol]}
                    onChange={(e) =>
                      setManualSelection((prev) => ({ ...prev, [symbol]: Number(e.target.value) }))
                    }
                  />
                  <span>%</span>
                </label>
              ))}
              <p className={`text-sm font-medium ${Math.abs(manualTotalWeight - 100) > 0.5 ? "text-rose-500" : "text-emerald-600"}`}>
                Total: {manualTotalWeight.toFixed(1)}%
              </p>
            </div>
          )}
        </InfoCard>
      )}

      {generating && (
        <InfoCard>
          <p className="mb-2 text-sm font-medium text-slate-600 dark:text-slate-300">{progressMessage}</p>
          <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-800">
            <div className="h-2 rounded-full bg-brand-gradient-soft transition-all" style={{ width: `${progress}%` }} />
          </div>
        </InfoCard>
      )}

      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="flex justify-center">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="rounded-full bg-brand-gradient-soft px-8 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30 transition-transform hover:-translate-y-0.5 disabled:opacity-60"
        >
          {generating ? "Generating..." : "Generate Portfolio →"}
        </button>
      </div>
    </div>
  );
}

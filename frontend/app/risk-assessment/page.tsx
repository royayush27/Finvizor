"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useWizardStore } from "@/lib/store";
import type { AnnualIncome, ExperienceLevel, FinancialGoal, InvestmentTimeline, RiskTolerance } from "@/lib/types";
import InfoCard from "@/components/InfoCard";

const EXPERIENCE_OPTIONS: ExperienceLevel[] = [
  "Beginner (0-2 years)",
  "Intermediate (2-5 years)",
  "Advanced (5-10 years)",
  "Expert (10+ years)",
];

const RISK_OPTIONS: RiskTolerance[] = [
  "Very Low Risk (Capital Preservation)",
  "Low Risk (Stable Growth)",
  "Medium Risk (Balanced Growth)",
  "High Risk (Aggressive Growth)",
  "Very High Risk (Maximum Returns)",
];

const TIMELINE_OPTIONS: InvestmentTimeline[] = ["< 1 Year", "1-3 Years", "3-5 Years", "5-10 Years", "> 10 Years"];

const GOAL_OPTIONS: FinancialGoal[] = [
  "Retirement planning",
  "Wealth preservation",
  "Income generation",
  "Capital appreciation",
  "Education funding",
  "Emergency fund growth",
];

const INCOME_OPTIONS: AnnualIncome[] = ["< $50K", "$50K - $100K", "$100K - $200K", "$200K - $500K", "> $500K"];

export default function RiskAssessmentPage() {
  const router = useRouter();
  const questionnaire = useWizardStore((s) => s.questionnaire);
  const setQuestionnaire = useWizardStore((s) => s.setQuestionnaire);
  const riskScore = useWizardStore((s) => s.riskScore);
  const riskLevel = useWizardStore((s) => s.riskLevel);
  const riskColor = useWizardStore((s) => s.riskColor);
  const setRiskScore = useWizardStore((s) => s.setRiskScore);

  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleContinue() {
    setScoring(true);
    setError(null);
    try {
      const response = await api.scoreRisk(questionnaire);
      setRiskScore(response.risk_score, response.risk_level, response.risk_color);
      router.push("/portfolio-builder");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the backend. Is it running?");
    } finally {
      setScoring(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold">Risk Assessment</h1>
        <p className="text-slate-500 dark:text-slate-400">
          Tell us about your investment preferences and risk tolerance.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Investment experience</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={questionnaire.experience_level}
            onChange={(e) => setQuestionnaire({ experience_level: e.target.value as ExperienceLevel })}
          >
            {EXPERIENCE_OPTIONS.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Investment timeline</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={questionnaire.investment_timeline}
            onChange={(e) => setQuestionnaire({ investment_timeline: e.target.value as InvestmentTimeline })}
          >
            {TIMELINE_OPTIONS.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Financial goal</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={questionnaire.financial_goal}
            onChange={(e) => setQuestionnaire({ financial_goal: e.target.value as FinancialGoal })}
          >
            {GOAL_OPTIONS.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Annual income</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={questionnaire.annual_income}
            onChange={(e) => setQuestionnaire({ annual_income: e.target.value as AnnualIncome })}
          >
            {INCOME_OPTIONS.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2 sm:col-span-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Investment amount (USD)
          </span>
          <input
            type="number"
            min={1000}
            max={10000000}
            step={1000}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            value={questionnaire.investment_amount}
            onChange={(e) => setQuestionnaire({ investment_amount: Number(e.target.value) })}
          />
        </label>
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Risk tolerance</h3>
        <div className="flex flex-col gap-2">
          {RISK_OPTIONS.map((option) => (
            <label
              key={option}
              className={`cursor-pointer rounded-xl border px-4 py-3 text-sm transition-colors ${
                questionnaire.risk_tolerance === option
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="risk_tolerance"
                className="mr-2"
                checked={questionnaire.risk_tolerance === option}
                onChange={() => setQuestionnaire({ risk_tolerance: option })}
              />
              {option}
            </label>
          ))}
        </div>
      </div>

      {riskScore !== null && (
        <InfoCard>
          <h4 className="mb-1 text-lg font-semibold">
            Risk Level: <span style={{ color: riskColor ?? undefined }}>{riskLevel}</span>
          </h4>
          <p className="text-sm text-slate-500 dark:text-slate-400">Risk Score: {riskScore}/100</p>
          <div className="mt-2 h-2 w-full rounded-full bg-slate-200 dark:bg-slate-800">
            <div
              className="h-2 rounded-full transition-all"
              style={{ width: `${riskScore}%`, backgroundColor: riskColor ?? "#667eea" }}
            />
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
          onClick={handleContinue}
          disabled={scoring}
          className="rounded-full bg-brand-gradient-soft px-8 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30 transition-transform hover:-translate-y-0.5 disabled:opacity-60"
        >
          {scoring ? "Scoring..." : "Continue to Portfolio Builder →"}
        </button>
      </div>
    </div>
  );
}

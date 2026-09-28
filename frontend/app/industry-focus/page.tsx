"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useWizardStore } from "@/lib/store";
import type { EsgPreference, IndustryInfo } from "@/lib/types";
import InfoCard from "@/components/InfoCard";

const ESG_OPTIONS: EsgPreference[] = ["No preference", "ESG-friendly preferred", "Strong ESG focus only"];

export default function IndustryFocusPage() {
  const router = useRouter();
  const [industries, setIndustries] = useState<IndustryInfo[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const industryFocus = useWizardStore((s) => s.industryFocus);
  const setIndustryFocus = useWizardStore((s) => s.setIndustryFocus);
  const excludeIndustries = useWizardStore((s) => s.excludeIndustries);
  const setExcludeIndustries = useWizardStore((s) => s.setExcludeIndustries);
  const esgPreference = useWizardStore((s) => s.esgPreference);
  const setEsgPreference = useWizardStore((s) => s.setEsgPreference);

  useEffect(() => {
    api
      .getIndustries()
      .then(setIndustries)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load industries."));
  }, []);

  function toggleFocus(key: string) {
    setIndustryFocus(industryFocus.includes(key) ? industryFocus.filter((i) => i !== key) : [...industryFocus, key]);
  }

  function toggleExclude(key: string) {
    setExcludeIndustries(
      excludeIndustries.includes(key) ? excludeIndustries.filter((i) => i !== key) : [...excludeIndustries, key]
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold">Industry Focus Selection</h1>
        <p className="text-slate-500 dark:text-slate-400">Choose industries you want to focus on or avoid.</p>
      </div>

      {loadError && (
        <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          {loadError}
        </div>
      )}

      <div>
        <h3 className="mb-3 text-lg font-semibold">Focus on</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {industries.map((industry) => {
            const selected = industryFocus.includes(industry.key);
            return (
              <button
                key={industry.key}
                onClick={() => toggleFocus(industry.key)}
                title={industry.description}
                className={`rounded-xl border p-4 text-center transition-all ${
                  selected
                    ? "border-transparent bg-brand-gradient-soft text-white shadow-lg shadow-indigo-500/30"
                    : "border-slate-200 bg-white hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
                }`}
              >
                <div className="text-2xl">{industry.icon}</div>
                <div className="mt-1 text-sm font-medium">{industry.key}</div>
              </button>
            );
          })}
        </div>
      </div>

      {industryFocus.length > 0 && (
        <InfoCard title="Your Industry Focus">
          <p className="text-sm text-slate-600 dark:text-slate-300">{industryFocus.join(", ")}</p>
        </InfoCard>
      )}

      <div>
        <h3 className="mb-2 text-lg font-semibold">Industries to avoid (optional)</h3>
        <div className="flex flex-wrap gap-2">
          {industries
            .filter((i) => !industryFocus.includes(i.key))
            .map((industry) => {
              const excluded = excludeIndustries.includes(industry.key);
              return (
                <button
                  key={industry.key}
                  onClick={() => toggleExclude(industry.key)}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    excluded
                      ? "border-rose-500 bg-rose-500 text-white"
                      : "border-slate-300 text-slate-600 hover:border-rose-400 dark:border-slate-700 dark:text-slate-300"
                  }`}
                >
                  {industry.icon} {industry.key}
                </button>
              );
            })}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Sustainable investing preference</h3>
        <div className="flex flex-col gap-2 sm:flex-row">
          {ESG_OPTIONS.map((option) => (
            <label
              key={option}
              className={`flex-1 cursor-pointer rounded-xl border px-4 py-3 text-sm transition-colors ${
                esgPreference === option
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="esg"
                className="mr-2"
                checked={esgPreference === option}
                onChange={() => setEsgPreference(option)}
              />
              {option}
            </label>
          ))}
        </div>
      </div>

      <div className="flex justify-center">
        <button
          onClick={() => {
            if (industryFocus.length >= 1) {
              router.push("/risk-assessment");
            }
          }}
          disabled={industryFocus.length < 1}
          className="rounded-full bg-brand-gradient-soft px-8 py-3 font-semibold text-white shadow-lg shadow-indigo-500/30 transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Continue to Risk Assessment →
        </button>
      </div>
      {industryFocus.length < 1 && (
        <p className="text-center text-sm text-amber-600 dark:text-amber-400">
          Please select at least one industry focus area.
        </p>
      )}
    </div>
  );
}

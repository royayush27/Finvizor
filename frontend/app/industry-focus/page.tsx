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
    setExcludeIndustries(excludeIndustries.filter((i) => i !== key));
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
        <h1 className="text-3xl font-bold">Define your universe.</h1>
        <p className="text-slate-500 ">Choose sectors to focus on or avoid. Leave the focus empty to consider all sectors.</p>
      </div>

      {loadError && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-red-700   ">
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
                aria-pressed={selected}
                onClick={() => toggleFocus(industry.key)}
                title={industry.description}
                className={`sector-option rounded-md border p-4 transition-colors ${
                  selected
                    ? "border-transparent bg-emerald-900 text-white  "
                    : "border-slate-200 bg-white    "
                }`}
              >
                <div className="mt-1 text-sm font-medium">{industry.key}</div>
                <small className="mt-2 block text-xs opacity-75">{industry.description}</small>
              </button>
            );
          })}
        </div>
      </div>

      {industryFocus.length > 0 && (
        <InfoCard title="Your Industry Focus">
          <p className="text-sm text-slate-600 ">{industryFocus.join(", ")}</p>
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
                  aria-pressed={excluded}
                  onClick={() => toggleExclude(industry.key)}
                  className={`rounded border px-3 py-1 text-sm transition-colors ${
                    excluded
                      ? "border-rose-500 bg-rose-500 text-white"
                      : "border-slate-300 text-slate-600 hover:border-rose-400  "
                  }`}
                >
                  {industry.key}
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
              className={`flex-1 rounded-md border px-4 py-3 text-sm transition-colors ${option !== "No preference" ? "cursor-not-allowed opacity-50" : "cursor-pointer"} ${
                esgPreference === option
                  ? "border-emerald-500 bg-emerald-50 text-emerald-700  "
                  : "border-slate-200 "
              }`}
            >
              <input
                type="radio"
                disabled={option !== "No preference"}
                name="esg"
                className="mr-2"
                checked={esgPreference === option}
                onChange={() => setEsgPreference(option)}
              />
              {option}
            </label>
          ))}
        </div>
        <p className="caption mt-3">ESG screening is not available yet. Verified ESG ratings are required before this filter can be applied.</p>
      </div>

      <div className="flex justify-center">
        <button
          onClick={() => {
            router.push("/risk-assessment");
          }}
          className="rounded bg-emerald-900 px-8 py-3 font-semibold text-white   transition-transform  disabled:cursor-not-allowed disabled:opacity-40"
        >
          Continue to Risk Assessment →
        </button>
      </div>
      {industryFocus.length < 1 && (
        <p className="text-center text-sm text-amber-600 ">
          All sectors will be considered.
        </p>
      )}
    </div>
  );
}

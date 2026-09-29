"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { EsgPreference, JobStatus, PortfolioResult, Questionnaire } from "./types";

// Replaces the original SessionStateManager (a Streamlit session_state
// wrapper). Persisting to localStorage is a real improvement over the
// original: a page refresh used to lose all wizard progress, since
// st.session_state only lives for the current browser session/tab.

const DEFAULT_QUESTIONNAIRE: Questionnaire = {
  experience_level: "Beginner (0-2 years)",
  risk_tolerance: "Medium Risk (Balanced Growth)",
  investment_timeline: "3-5 Years",
  investment_amount: 10000,
  financial_goal: "Retirement planning",
  annual_income: "$50K - $100K",
};

interface WizardState {
  industryFocus: string[];
  excludeIndustries: string[];
  esgPreference: EsgPreference;
  questionnaire: Questionnaire;
  riskScore: number | null;
  riskLevel: string | null;
  riskColor: string | null;
  activeJob: JobStatus | null;
  portfolio: PortfolioResult | null;

  setIndustryFocus: (industries: string[]) => void;
  setExcludeIndustries: (industries: string[]) => void;
  setEsgPreference: (preference: EsgPreference) => void;
  setQuestionnaire: (partial: Partial<Questionnaire>) => void;
  setRiskScore: (score: number, level: string, color: string) => void;
  setActiveJob: (job: JobStatus | null) => void;
  setPortfolio: (portfolio: PortfolioResult | null) => void;
  resetWizard: () => void;
}

export const useWizardStore = create<WizardState>()(
  persist(
    (set) => ({
      industryFocus: [],
      excludeIndustries: [],
      esgPreference: "No preference",
      questionnaire: DEFAULT_QUESTIONNAIRE,
      riskScore: null,
      riskLevel: null,
      riskColor: null,
      activeJob: null,
      portfolio: null,

      setIndustryFocus: (industries) => set({ industryFocus: industries }),
      setExcludeIndustries: (industries) => set({ excludeIndustries: industries }),
      setEsgPreference: (preference) => set({ esgPreference: preference }),
      setQuestionnaire: (partial) => set((state) => ({ questionnaire: { ...state.questionnaire, ...partial }, riskScore: null, riskLevel: null, riskColor: null })),
      setRiskScore: (score, level, color) => set({ riskScore: score, riskLevel: level, riskColor: color }),
      setActiveJob: (job) => set({ activeJob: job }),
      setPortfolio: (portfolio) => set({ portfolio }),
      resetWizard: () =>
        set({
          industryFocus: [],
          excludeIndustries: [],
          esgPreference: "No preference",
          questionnaire: DEFAULT_QUESTIONNAIRE,
          riskScore: null,
          riskLevel: null,
          riskColor: null,
          activeJob: null,
          portfolio: null,
        }),
    }),
    { name: "finvizor-wizard-state", version: 2 }
  )
);

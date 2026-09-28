"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const STEPS = [
  { href: "/", label: "Welcome" },
  { href: "/industry-focus", label: "Industry Focus" },
  { href: "/risk-assessment", label: "Risk Assessment" },
  { href: "/portfolio-builder", label: "Portfolio Builder" },
  { href: "/results", label: "Results" },
];

export default function StepNav() {
  const pathname = usePathname();
  const activeIndex = STEPS.findIndex((s) => s.href === pathname);

  return (
    <nav className="mb-8 flex items-center justify-between overflow-x-auto rounded-2xl bg-gradient-to-r from-slate-100 to-slate-200 p-3 shadow-inner dark:from-slate-900 dark:to-slate-800">
      {STEPS.map((step, index) => {
        const isActive = index === activeIndex;
        const isCompleted = activeIndex >= 0 && index < activeIndex;
        return (
          <Link
            key={step.href}
            href={step.href}
            className="group flex flex-1 flex-col items-center gap-1 px-2 text-center no-underline"
          >
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-all ${
                isActive
                  ? "scale-110 bg-brand-gradient-soft text-white shadow-lg shadow-indigo-500/40"
                  : isCompleted
                    ? "bg-emerald-500 text-white"
                    : "bg-white text-slate-500 ring-1 ring-slate-300 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-700"
              }`}
            >
              {index + 1}
            </span>
            <span className="text-xs font-medium text-slate-600 group-hover:text-slate-900 dark:text-slate-400 dark:group-hover:text-slate-100">
              {step.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

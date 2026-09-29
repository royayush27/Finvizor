"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const STEPS = [
  { href: "/", label: "Overview" },
  { href: "/industry-focus", label: "Sectors" },
  { href: "/risk-assessment", label: "Risk profile" },
  { href: "/portfolio-builder", label: "Allocation" },
  { href: "/results", label: "Research report" },
];
export default function StepNav() {
  const pathname = usePathname();
  return <nav className="step-nav" aria-label="Portfolio workflow">{STEPS.map((step, index) => (
    <Link key={step.href} href={step.href} aria-current={pathname === step.href ? "step" : undefined}>
      <span className="step-number">{String(index + 1).padStart(2, "0")}</span>{step.label}
    </Link>
  ))}</nav>;
}

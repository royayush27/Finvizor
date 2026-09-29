import type { Metadata } from "next";
import "./globals.css";
import StepNav from "@/components/StepNav";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Finvizor | Portfolio Research",
  description: "Explore US equity allocations, historical returns, and portfolio risk.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="skip-link">Skip to content</a>
        <div className="app-shell">
          <header className="masthead"><Link href="/" className="wordmark"><span className="brand-mark" aria-hidden="true">f.</span>finvizor<span className="wordmark-detail">RESEARCH</span></Link><span className="masthead-label">An independent view of your portfolio.</span><span className="market-label">US / USD</span></header>
          <StepNav />
          <div className="workspace-grid">
            <main id="main-content">{children}</main>
            <Sidebar />
          </div>
          <footer className="app-footer"><span>Finvizor / Portfolio research</span><span>Educational use. No brokerage or trade execution.</span></footer>
        </div>
      </body>
    </html>
  );
}

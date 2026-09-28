import type { Metadata } from "next";
import "./globals.css";
import StepNav from "@/components/StepNav";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Finvizor Pro | AI Portfolio Builder",
  description: "AI-powered portfolio construction: ML return prediction, FRED economic data, and news-sentiment filtering.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          <StepNav />
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_260px]">
            <main>{children}</main>
            <Sidebar />
          </div>
        </div>
      </body>
    </html>
  );
}

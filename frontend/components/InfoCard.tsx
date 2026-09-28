interface InfoCardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export default function InfoCard({ title, children, className = "" }: InfoCardProps) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-md shadow-slate-900/5 backdrop-blur transition-shadow hover:shadow-lg dark:border-slate-800 dark:bg-slate-900/80 ${className}`}
    >
      {title && <h4 className="mb-2 text-lg font-semibold text-slate-800 dark:text-slate-100">{title}</h4>}
      {children}
    </div>
  );
}

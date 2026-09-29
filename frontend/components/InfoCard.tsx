interface InfoCardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export default function InfoCard({ title, children, className = "" }: InfoCardProps) {
  return (
    <div
      className={`panel ${className}`}
    >
      {title && <h4 className="mb-2 text-lg font-semibold text-slate-800 ">{title}</h4>}
      {children}
    </div>
  );
}

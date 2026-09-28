interface MetricCardProps {
  value: string;
  label: string;
}

export default function MetricCard({ value, label }: MetricCardProps) {
  return (
    <div className="rounded-2xl bg-brand-gradient-soft p-6 text-center text-white shadow-lg shadow-indigo-500/20 transition-transform hover:-translate-y-1">
      <div className="text-3xl font-bold">{value}</div>
      <div className="mt-1 text-sm text-white/90">{label}</div>
    </div>
  );
}

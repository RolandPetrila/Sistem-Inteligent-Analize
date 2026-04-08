export function SimpleBarChart({
  data,
  years,
  label,
  color,
  unit,
}: {
  data: (number | null)[];
  years: string[];
  label: string;
  color: string;
  unit?: string;
}) {
  if (!data || data.every((v) => v === null)) return null;
  const valid = data.filter((v): v is number => v !== null);
  const max = Math.max(...valid);
  if (max === 0) return null;
  const W = 280;
  const H = 80;
  const BAR_W = Math.max(10, Math.floor(W / data.length) - 4);
  return (
    <div className="space-y-1">
      <p className="text-xs text-gray-400">
        {label}
        {unit ? ` (${unit})` : ""}
      </p>
      <svg width={W} height={H} className="overflow-visible">
        {data.map((v, i) => {
          if (v === null) return null;
          const barH = Math.max(2, (v / max) * (H - 16));
          const x = i * (BAR_W + 4);
          return (
            <g key={i}>
              <rect
                x={x}
                y={H - barH - 16}
                width={BAR_W}
                height={barH}
                fill={color}
                rx={2}
                opacity={0.8}
              />
              <text
                x={x + BAR_W / 2}
                y={H - 4}
                fontSize={8}
                fill="#9ca3af"
                textAnchor="middle"
              >
                {years[i]}
              </text>
              <text
                x={x + BAR_W / 2}
                y={H - barH - 18}
                fontSize={7}
                fill="#9ca3af"
                textAnchor="middle"
              >
                {v >= 1000 ? `${(v / 1000).toFixed(0)}K` : String(v)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

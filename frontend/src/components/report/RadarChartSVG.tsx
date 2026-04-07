interface RadarChartSVGProps {
  scoringDimensions: Record<string, { score: number; weight: number }>;
}

const DIMS = [
  "financiar",
  "juridic",
  "fiscal",
  "operational",
  "reputational",
  "piata",
] as const;
const LABELS = [
  "Financiar",
  "Juridic",
  "Fiscal",
  "Operational",
  "Reputational",
  "Piata",
];
const GRID_LEVELS = [0.25, 0.5, 0.75, 1.0];

const CX = 120;
const CY = 120;
const R = 90;

function getAxisPoint(i: number, n: number, radius: number): [number, number] {
  const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
  return [CX + radius * Math.cos(angle), CY + radius * Math.sin(angle)];
}

export function RadarChartSVG({ scoringDimensions }: RadarChartSVGProps) {
  const n = DIMS.length;

  const dataPoints = DIMS.map((d, i) => {
    const val = ((scoringDimensions[d]?.score ?? 50) / 100) * R;
    return getAxisPoint(i, n, val);
  });

  return (
    <div className="p-3 bg-dark-surface rounded-lg mb-4">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Profil Risc Radar
      </h4>
      <div className="flex justify-center">
        <svg width="240" height="240" viewBox="0 0 240 240">
          {/* Grid polygons */}
          {GRID_LEVELS.map((lvl, gi) => {
            const gridPts = DIMS.map((_, i) => {
              const [x, y] = getAxisPoint(i, n, lvl * R);
              return `${x},${y}`;
            }).join(" ");
            return (
              <polygon
                key={gi}
                points={gridPts}
                fill="none"
                stroke="#374151"
                strokeWidth="1"
              />
            );
          })}

          {/* Axes */}
          {DIMS.map((_, i) => {
            const [x2, y2] = getAxisPoint(i, n, R);
            return (
              <line
                key={i}
                x1={CX}
                y1={CY}
                x2={x2}
                y2={y2}
                stroke="#374151"
                strokeWidth="1"
              />
            );
          })}

          {/* Data polygon */}
          <polygon
            points={dataPoints.map((p) => p.join(",")).join(" ")}
            fill="rgba(99,102,241,0.25)"
            stroke="#6366f1"
            strokeWidth="2"
          />

          {/* Labels */}
          {LABELS.map((lbl, i) => {
            const [lx, ly] = getAxisPoint(i, n, R + 18);
            return (
              <text
                key={i}
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#9ca3af"
                fontSize="9"
              >
                {lbl}
              </text>
            );
          })}

          {/* Score dots on axes */}
          {DIMS.map((d, i) => {
            const score = scoringDimensions[d]?.score ?? 0;
            const val = (score / 100) * R;
            const [px, py] = getAxisPoint(i, n, val);
            return <circle key={i} cx={px} cy={py} r="3" fill="#6366f1" />;
          })}
        </svg>
      </div>
    </div>
  );
}

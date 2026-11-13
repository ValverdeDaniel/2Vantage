// The small area sparkline under the Work queue's graph cards (old CasesDashboard.jsx at 891f1b3, hand-rolled SVG, no
// chart library), now drawn from real figures (I127; OQ94): the server's ten points, oldest first. Scaling a line to
// its box is drawing, not money math. A flat or empty series draws a flat line along the bottom.

export default function Sparkline({ data, color, width = 104, height = 46 }) {
  const points = data?.length ? data.map(Number) : [0, 0];
  const pad = 3;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (points.length - 1 || 1);
  const xy = points.map((value, index) => [
    pad + index * stepX,
    pad + (height - pad * 2) * (1 - (max === min ? 0 : (value - min) / span)),
  ]);
  const line = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const base = (height - pad).toFixed(1);
  const area = `M${xy[0][0].toFixed(1)},${base} ${xy.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(' ')} L${xy[xy.length - 1][0].toFixed(1)},${base} Z`;
  const gradient = `spark-${color.replace('#', '')}`;
  return (
    <svg
      className="bnf-spark"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradient})`} />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

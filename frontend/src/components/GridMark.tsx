// Eight circular dots in a 3×3 pattern with the bottom-right missing.
// Sits inline as a glyph — no container tile — so the mark reads as
// dots rather than a stack of squares.

interface GridMarkProps {
  size?: number
  className?: string
}

export function GridMark({ size = 24, className = '' }: GridMarkProps) {
  const unit = size / 7
  const dot = unit * 1.6
  const gap = unit * 0.9
  const span = dot * 3 + gap * 2
  const dots: Array<[number, number]> = []
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      if (r === 2 && c === 2) continue
      dots.push([c, r])
    }
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${span} ${span}`}
      className={`text-ink-1 ${className}`}
      aria-hidden="true"
    >
      {dots.map(([c, r], i) => (
        <circle
          key={i}
          cx={c * (dot + gap) + dot / 2}
          cy={r * (dot + gap) + dot / 2}
          r={dot / 2}
          fill="currentColor"
        />
      ))}
    </svg>
  )
}

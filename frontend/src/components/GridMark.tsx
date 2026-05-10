// The 3×3 grid mark from decade.com — eight dots in a square, bottom-right
// dot intentionally missing. Stand-alone component so we can size it
// consistently across header, footer, hero, and the access-gate card.

interface GridMarkProps {
  size?: number
  className?: string
}

export function GridMark({ size = 24, className = '' }: GridMarkProps) {
  const dot = (size - 4) / 5
  const gap = dot * 0.4
  const padding = dot * 0.4
  const dots: Array<[number, number]> = []
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      if (r === 2 && c === 2) continue
      dots.push([c, r])
    }
  }
  return (
    <span
      className={`inline-flex items-center justify-center bg-surface-2 ${className}`}
      style={{ width: size, height: size, borderRadius: size * 0.16 }}
      aria-hidden="true"
    >
      <svg
        width={size - padding * 2}
        height={size - padding * 2}
        viewBox={`0 0 ${dot * 3 + gap * 2} ${dot * 3 + gap * 2}`}
      >
        {dots.map(([c, r], i) => (
          <rect
            key={i}
            x={c * (dot + gap)}
            y={r * (dot + gap)}
            width={dot}
            height={dot}
            rx={dot * 0.15}
            fill="currentColor"
            className="text-ink-1"
          />
        ))}
      </svg>
    </span>
  )
}

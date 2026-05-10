import type { ReactNode } from 'react'

// A definition-list item used inside Failure modes / Trade-offs sections.
// Term + body, neutral typography. No icons, no decorative borders.

interface SpecItemProps {
  term: ReactNode
  children: ReactNode
}

export function SpecItem({ term, children }: SpecItemProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[14rem_1fr] gap-x-8 gap-y-1 py-3 border-t border-border first:border-t-0">
      <dt className="text-ink-1 text-[14px] font-medium tracking-tight pt-px">{term}</dt>
      <dd className="text-ink-2 text-[15px] leading-relaxed">{children}</dd>
    </div>
  )
}

export function SpecList({ children }: { children: ReactNode }) {
  return <dl className="my-2">{children}</dl>
}

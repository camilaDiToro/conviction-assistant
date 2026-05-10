import type { ReactNode } from 'react'

interface SectionProps {
  eyebrow?: string
  title?: ReactNode
  lead?: ReactNode
  children?: ReactNode
  id?: string
}

// A single content section: small uppercase eyebrow, large display title,
// optional lead paragraph, then body. The visual rhythm of every page.
export function Section({ eyebrow, title, lead, children, id }: SectionProps) {
  return (
    <section id={id} className="py-12 md:py-20 first:pt-0">
      <div className="max-w-prose">
        {eyebrow && (
          <div className="pill mb-6">{eyebrow}</div>
        )}
        {title && (
          <h2 className="text-display-2 text-ink-1 mb-6 text-balance">{title}</h2>
        )}
        {lead && (
          <p className="text-ink-2 text-lg leading-relaxed mb-8 text-balance">{lead}</p>
        )}
      </div>
      {children}
    </section>
  )
}

interface PageHeaderProps {
  eyebrow: string
  title: ReactNode
  lead?: ReactNode
}

export function PageHeader({ eyebrow, title, lead }: PageHeaderProps) {
  return (
    <header className="pt-2 pb-12 md:pb-20 border-b border-border mb-12 md:mb-16 animate-fade-in">
      <div className="pill mb-6">{eyebrow}</div>
      <h1 className="text-display-1 text-ink-1 mb-6 text-balance max-w-[20ch]">{title}</h1>
      {lead && (
        <p className="text-ink-2 text-lg md:text-xl leading-relaxed max-w-prose text-balance">{lead}</p>
      )}
    </header>
  )
}

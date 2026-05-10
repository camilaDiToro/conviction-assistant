import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

interface CodeBlockProps {
  code: string
  lang?: string
  caption?: string
}

export function CodeBlock({ code, lang, caption }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }
  return (
    <figure className="my-6">
      <div className="relative group bg-surface border border-border rounded-md overflow-hidden">
        {lang && (
          <div className="absolute top-2.5 left-3 text-[10px] uppercase tracking-tight text-ink-3 font-mono">
            {lang}
          </div>
        )}
        <button
          onClick={onCopy}
          aria-label="Copy code"
          className="absolute top-2 right-2 text-ink-3 hover:text-ink-1 transition-colors p-1.5 opacity-0 group-hover:opacity-100"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
        <pre className="font-mono text-[13px] leading-relaxed text-ink-1 p-4 pt-9 overflow-x-auto">
          <code>{code}</code>
        </pre>
      </div>
      {caption && (
        <figcaption className="text-ink-3 text-xs mt-2 leading-relaxed">{caption}</figcaption>
      )}
    </figure>
  )
}

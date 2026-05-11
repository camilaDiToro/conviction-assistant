// User-facing override panel for the agent loop knobs. Loads server
// defaults + allowed values from GET /api/config and persists the
// user's choices in localStorage via lib/chat-prefs. Every active field
// is sent on the next /chat request (see api.ts).

import { useEffect, useMemo, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { loadConfig, UnauthorizedError } from '@/lib/api'
import type { ChatOverrides, ConfigResponse, ReasoningEffort } from '@/lib/types'
import { clearChatPrefs, readChatPrefs, writeChatPrefs } from '@/lib/chat-prefs'

const EFFORTS: ReasoningEffort[] = ['minimal', 'low', 'medium', 'high']

interface SettingsDrawerProps {
  onClose: () => void
  onUnauthorized: () => void
  onPrefsChange: () => void
}

export function SettingsDrawer({ onClose, onUnauthorized, onPrefsChange }: SettingsDrawerProps) {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [prefs, setPrefs] = useState<ChatOverrides>(() => readChatPrefs() ?? {})

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    let alive = true
    loadConfig()
      .then(c => {
        if (alive) setConfig(c)
      })
      .catch(e => {
        if (!alive) return
        if (e instanceof UnauthorizedError) {
          onUnauthorized()
          return
        }
        setLoadError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      alive = false
    }
  }, [onUnauthorized])

  const update = (patch: Partial<ChatOverrides>) => {
    const next: ChatOverrides = { ...prefs, ...patch }
    // Drop keys that match the default — keeps the wire payload empty
    // when nothing is being overridden.
    if (config) {
      if (next.model === config.defaults.model) delete next.model
      if (next.reasoning_effort === config.defaults.reasoning_effort) delete next.reasoning_effort
      if (next.rewrite_reasoning_effort === config.defaults.rewrite_reasoning_effort)
        delete next.rewrite_reasoning_effort
      if (next.agent_max_tool_calls === config.defaults.agent_max_tool_calls)
        delete next.agent_max_tool_calls
      if (next.agent_max_output_tokens === config.defaults.agent_max_output_tokens)
        delete next.agent_max_output_tokens
    }
    setPrefs(next)
    if (Object.keys(next).length === 0) clearChatPrefs()
    else writeChatPrefs(next)
    onPrefsChange()
  }

  const reset = () => {
    setPrefs({})
    clearChatPrefs()
    onPrefsChange()
  }

  const effective = useMemo(() => {
    if (!config) return null
    return {
      model: prefs.model ?? config.defaults.model,
      reasoning_effort: prefs.reasoning_effort ?? config.defaults.reasoning_effort,
      rewrite_reasoning_effort:
        prefs.rewrite_reasoning_effort ?? config.defaults.rewrite_reasoning_effort,
      agent_max_tool_calls:
        prefs.agent_max_tool_calls ?? config.defaults.agent_max_tool_calls,
      agent_max_output_tokens:
        prefs.agent_max_output_tokens ?? config.defaults.agent_max_output_tokens,
    }
  }, [prefs, config])

  const overrideKeys = Object.keys(prefs)

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-bg/80 backdrop-blur-sm" onClick={onClose} />
      <aside className="w-full max-w-md bg-bg border-l border-border overflow-y-auto animate-fade-in">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between sticky top-0 bg-bg">
          <div>
            <div className="text-ink-3 text-[10px] uppercase tracking-tight">Settings</div>
            <h3 className="text-ink-1 font-medium">Agent configuration</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="text-ink-3 hover:text-ink-1 p-1"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-8">
          {!config && !loadError && (
            <div className="flex items-center gap-2 text-ink-3 text-xs">
              <Loader2 size={12} className="animate-spin" /> Loading config…
            </div>
          )}
          {loadError && (
            <div className="text-ink-2 text-xs border border-border bg-surface rounded-md p-3">
              <strong className="text-ink-1 font-medium block mb-1">Failed to load config.</strong>
              {loadError}
            </div>
          )}

          {config && effective && (
            <>
              <section className="space-y-3">
                <div>
                  <label className="text-ink-3 text-[10px] uppercase tracking-tight block mb-2">
                    Model
                  </label>
                  <select
                    value={effective.model}
                    onChange={e => update({ model: e.target.value })}
                    className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-1 font-mono text-[12px] focus:border-ink-1 outline-none"
                  >
                    {config.allowed_models.map(m => (
                      <option key={m} value={m}>
                        {m}
                        {m === config.defaults.model ? ' (default)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </section>

              <section className="space-y-3">
                <div>
                  <label className="text-ink-3 text-[10px] uppercase tracking-tight block mb-2">
                    Reasoning effort (agent loop)
                  </label>
                  <EffortRadio
                    name="agent_reasoning"
                    value={effective.reasoning_effort}
                    defaultValue={config.defaults.reasoning_effort}
                    options={config.allowed_reasoning_efforts}
                    onChange={v => update({ reasoning_effort: v })}
                  />
                </div>
                <div>
                  <label className="text-ink-3 text-[10px] uppercase tracking-tight block mb-2">
                    Reasoning effort (rewrite)
                  </label>
                  <EffortRadio
                    name="rewrite_reasoning"
                    value={effective.rewrite_reasoning_effort}
                    defaultValue={config.defaults.rewrite_reasoning_effort}
                    options={config.allowed_reasoning_efforts}
                    onChange={v => update({ rewrite_reasoning_effort: v })}
                  />
                </div>
              </section>

              <section className="space-y-4">
                <NumberSlider
                  label="Max tool calls"
                  value={effective.agent_max_tool_calls}
                  defaultValue={config.defaults.agent_max_tool_calls}
                  min={config.limits.agent_max_tool_calls?.min ?? 1}
                  max={config.limits.agent_max_tool_calls?.max ?? 10}
                  step={1}
                  onChange={v => update({ agent_max_tool_calls: v })}
                />
                <NumberSlider
                  label="Max output tokens"
                  value={effective.agent_max_output_tokens}
                  defaultValue={config.defaults.agent_max_output_tokens}
                  min={config.limits.agent_max_output_tokens?.min ?? 256}
                  max={config.limits.agent_max_output_tokens?.max ?? 16384}
                  step={256}
                  onChange={v => update({ agent_max_output_tokens: v })}
                />
              </section>

              <section className="flex items-center justify-between pt-4 border-t border-border">
                <div className="text-ink-3 text-[11px] font-mono">
                  {overrideKeys.length === 0
                    ? 'All defaults'
                    : `${overrideKeys.length} override${overrideKeys.length === 1 ? '' : 's'} active`}
                </div>
                <button
                  onClick={reset}
                  disabled={overrideKeys.length === 0}
                  className="text-[11px] uppercase tracking-tight text-ink-3 hover:text-ink-1 disabled:opacity-30 disabled:hover:text-ink-3 transition-colors"
                >
                  Reset to defaults
                </button>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

function EffortRadio({
  name,
  value,
  defaultValue,
  options,
  onChange,
}: {
  name: string
  value: ReasoningEffort
  defaultValue: ReasoningEffort
  options: ReasoningEffort[]
  onChange: (v: ReasoningEffort) => void
}) {
  const effortOptions = (options.length > 0 ? options : EFFORTS) as ReasoningEffort[]
  return (
    <div className="grid grid-cols-4 gap-px bg-border border border-border rounded-md overflow-hidden">
      {effortOptions.map(o => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={`px-2 py-2 text-[11px] uppercase tracking-tight transition-colors ${
            value === o ? 'bg-ink-1 text-bg' : 'bg-surface text-ink-2 hover:text-ink-1'
          }`}
        >
          {o}
          {o === defaultValue ? ' •' : ''}
        </button>
      ))}
      <input type="hidden" name={name} value={value} />
    </div>
  )
}

function NumberSlider({
  label,
  value,
  defaultValue,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  value: number
  defaultValue: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <label className="text-ink-3 text-[10px] uppercase tracking-tight">{label}</label>
        <span className="font-mono text-[12px] text-ink-1">
          {value}
          {value === defaultValue ? <span className="text-ink-3 ml-1">(default)</span> : null}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-ink-1"
      />
      <div className="flex justify-between text-ink-4 text-[10px] font-mono mt-1">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}

// Per-user overrides for the chat agent loop (model, reasoning, limits).
// Persisted in localStorage; null fields mean "use server default". The
// backend honours these via ChatRequest.overrides; GET /api/config tells
// the SettingsDrawer which defaults/allowed values to show.

import type { ChatOverrides } from './types'

const STORAGE_KEY = 'chat_prefs'

export function readChatPrefs(): ChatOverrides | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<ChatOverrides>
    const filtered: ChatOverrides = {}
    if (parsed.model) filtered.model = parsed.model
    if (parsed.reasoning_effort) filtered.reasoning_effort = parsed.reasoning_effort
    if (parsed.rewrite_reasoning_effort)
      filtered.rewrite_reasoning_effort = parsed.rewrite_reasoning_effort
    if (typeof parsed.agent_max_tool_calls === 'number')
      filtered.agent_max_tool_calls = parsed.agent_max_tool_calls
    if (typeof parsed.agent_max_output_tokens === 'number')
      filtered.agent_max_output_tokens = parsed.agent_max_output_tokens
    return Object.keys(filtered).length ? filtered : null
  } catch {
    return null
  }
}

export function writeChatPrefs(prefs: ChatOverrides): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

export function clearChatPrefs(): void {
  localStorage.removeItem(STORAGE_KEY)
}

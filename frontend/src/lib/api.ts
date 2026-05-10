// *** SINGLE POINT OF BACKEND INTERACTION ***
// No fetch() calls anywhere else in the frontend. ESLint rule enforces this.
//
// Today: chat returns from the local mock (real /chat lands in B9).
// When B9 lands: flip USE_MOCK_CHAT to false. The mock keeps the contract
// faithful, so no other code changes.

import type { ChatResponse } from './types'
import { mockChat } from './mock-chat'

const USE_MOCK_CHAT = true

export interface SendChatArgs {
  question: string
  conversationId: string
  history: Array<{ role: 'user' | 'assistant'; content: string }>
}

export async function sendChatMessage(args: SendChatArgs): Promise<ChatResponse> {
  if (USE_MOCK_CHAT) {
    return mockChat(args)
  }
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  })
  if (!res.ok) throw new Error(`/chat failed: ${res.status}`)
  return (await res.json()) as ChatResponse
}

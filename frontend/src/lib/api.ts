// *** SINGLE POINT OF BACKEND INTERACTION ***
// No fetch() calls anywhere else in the frontend. ESLint rule enforces this.
//
// B9: real /chat is live. The chat token is read from localStorage (set
// by the gate UI) and sent as `X-Chat-Token` on every request. On 401
// the token is cleared and an UnauthorizedError is thrown so the UI can
// re-prompt for it.

import type {
  ChatResponse,
  ConversationListResponse,
  ConversationMessagesResponse,
} from './types'
import { clearToken, readToken } from './access-gate'

export class UnauthorizedError extends Error {
  constructor(message = 'unauthorized') {
    super(message)
    this.name = 'UnauthorizedError'
  }
}

export interface SendChatArgs {
  question: string
  conversationId?: string
  history: Array<{ role: 'user' | 'assistant'; content: string }>
}

export async function sendChatMessage(args: SendChatArgs): Promise<ChatResponse> {
  const token = readToken()
  if (!token) throw new UnauthorizedError('no chat token configured')

  const res = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Chat-Token': token,
    },
    body: JSON.stringify({
      question: args.question,
      conversation_id: args.conversationId,
      history: args.history,
    }),
  })

  if (res.status === 401) {
    clearToken()
    throw new UnauthorizedError(`/chat rejected token (${res.status})`)
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`/chat failed: ${res.status} ${detail}`)
  }
  return (await res.json()) as ChatResponse
}

async function getJson<T>(path: string): Promise<T> {
  const token = readToken()
  if (!token) throw new UnauthorizedError('no chat token configured')
  const res = await fetch(path, { headers: { 'X-Chat-Token': token } })
  if (res.status === 401) {
    clearToken()
    throw new UnauthorizedError(`${path} rejected token (${res.status})`)
  }
  if (res.status === 404) {
    const err = new Error(`${path}: not found`) as Error & { status?: number }
    err.status = 404
    throw err
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${path} failed: ${res.status} ${detail}`)
  }
  return (await res.json()) as T
}

export async function listConversations(): Promise<ConversationListResponse> {
  return getJson<ConversationListResponse>('/chat/conversations')
}

export async function loadConversation(
  conversationId: string,
): Promise<ConversationMessagesResponse> {
  return getJson<ConversationMessagesResponse>(
    `/chat/conversations/${encodeURIComponent(conversationId)}`,
  )
}

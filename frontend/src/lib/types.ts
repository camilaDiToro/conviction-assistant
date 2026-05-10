// Mirrored from app/schemas/passage.py and the planned /chat response.
// Keep in sync with the backend schemas. The chat response shape is the
// contract documented in CLAUDE.md (lands behind /chat in B9).

export interface Passage {
  id: string
  document_id: string
  document_title: string
  heading: string
  heading_path: string[]
  text: string
  document_updated: string | null // ISO date
}

export interface DocSummary {
  id: string
  title: string
  document_updated: string | null
  passage_count: number
}

export interface Heading {
  passage_id: string
  heading: string
  ordinal: number
}

export interface DocumentOutline {
  document_id: string
  document_title: string
  document_updated: string | null
  passage_count: number
  headings: Heading[]
}

export interface PassageHit {
  passage_id: string
  score: number
  document_id: string
  document_title: string
  heading_path: string[]
  snippet: string
  document_updated: string | null
}

// ----- Chat contract (B9) -----

export interface Citation {
  passage_id: string
  document: string
  document_updated: string | null
  heading: string
  heading_path: string[]
  quote: string
}

export interface TokenUsage {
  model: string
  prompt_tokens: number
  completion_tokens: number
  cached_tokens: number
  reasoning_tokens: number
}

export interface DebugStep {
  step_id: string
  kind: 'llm_call' | 'tool_call' | 'verifier' | 'response'
  name: string
  detail: string
  duration_ms: number
  usage?: TokenUsage
  cost_usd?: number
}

export interface UsageSummary {
  question_total_cost_usd: number
  conversation_total_cost_usd: number
  step_count: number
}

export interface ChatAnswerResponse {
  kind: 'answer'
  answer: string
  citations: Citation[]
  general_knowledge_used: boolean
  general_knowledge_section: string | null
  out_of_scope: boolean
  disclaimer: string
  usage_summary: UsageSummary
  debug: { tool_calls: DebugStep[]; verification_passed: boolean; steps: DebugStep[] }
}

export interface ChatClarifyResponse {
  kind: 'clarifying_question'
  question: string
  options: string[]
  disclaimer: string
  usage_summary: UsageSummary
  debug: { tool_calls: DebugStep[]; verification_passed: boolean; steps: DebugStep[] }
}

export type ChatResponse = ChatAnswerResponse | ChatClarifyResponse

export interface ChatMessageUser {
  role: 'user'
  content: string
  id: string
}

export interface ChatMessageAssistant {
  role: 'assistant'
  response: ChatResponse
  id: string
}

export type ChatMessage = ChatMessageUser | ChatMessageAssistant

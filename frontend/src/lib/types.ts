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
  passage_text: string
  // Half-open offsets into `passage_text`. Both null when the model's quote
  // didn't anchor — the popup shows the passage without a highlight.
  start: number | null
  end: number | null
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
  kind: 'llm_call' | 'tool_call' | 'resolver' | 'response'
  name: string
  detail: string
  duration_ms: number
  usage: TokenUsage | null
  cost_usd: number | null
  // Step-kind-specific JSON summary of what the step produced.
  // tool_call → { result: <tool return value> }
  // llm_call  → { tool_calls?, parsed?, content? }
  // resolver  → { entries: CitationResolution[] }
  // response  → { output: AnswerOutput | ClarifyingQuestionOutput, resolution_entries? }
  result: Record<string, unknown> | null
}

export interface UsageSummary {
  question_total_cost_usd: number
  conversation_total_cost_usd: number
  step_count: number
  duration_ms: number
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
  debug: { tool_calls: DebugStep[]; steps: DebugStep[] }
  conversation_id: string
  question_id: string
}

export interface ChatClarifyResponse {
  kind: 'clarifying_question'
  question: string
  options: string[]
  disclaimer: string
  usage_summary: UsageSummary
  debug: { tool_calls: DebugStep[]; steps: DebugStep[] }
  conversation_id: string
  question_id: string
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

// ----- Conversation history (sidebar) -----

export interface ConversationListItem {
  conversation_id: string
  title: string
  first_ts: string // ISO datetime
  last_ts: string
  question_count: number
}

export interface ConversationListResponse {
  conversations: ConversationListItem[]
}

export interface ConversationMessage {
  question_id: string
  timestamp: string
  user_question: string
  language: 'pt' | 'en' | 'es'
  kind: 'answer' | 'clarifying_question'
  answer: string | null
  citations: Citation[]
  general_knowledge_used: boolean | null
  general_knowledge_section: string | null
  out_of_scope: boolean | null
  clarifying_question: string | null
  clarifying_options: string[]
}

export interface ConversationMessagesResponse {
  conversation_id: string
  messages: ConversationMessage[]
}

export interface QuestionStepsResponse {
  conversation_id: string
  question_id: string
  steps: DebugStep[]
  usage_summary: UsageSummary
}

// Demo gate for the chat surface. Anyone with bundle access can read
// VITE_CHAT_ACCESS_CODE — this is friction, not security. Real auth is
// deliberately out of scope for v1.

const STORAGE_KEY = 'decade-chat-unlocked'

export function readUnlocked(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

export function setUnlocked(unlocked: boolean): void {
  try {
    if (unlocked) localStorage.setItem(STORAGE_KEY, 'true')
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* localStorage disabled — gate becomes session-only */
  }
}

export function checkCode(input: string): boolean {
  const expected = (import.meta.env.VITE_CHAT_ACCESS_CODE ?? '').trim()
  if (!expected) return false
  return input.trim() === expected
}

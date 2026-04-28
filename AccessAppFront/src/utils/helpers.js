/** General helper utilities for ids, retries, and assistant-response text normalization. */
export function createId() {
  // Builds a lightweight client-side id for optimistic rows before backend ids exist.
  return Date.now() + Math.floor(Math.random() * 1000)
}

export function wait(ms) {
  // Promise-based sleep utility used by retry and pacing helpers.
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function withSingleRetry(task) {
  // Executes a task once, then retries a single time after a short delay if the first attempt fails.
  try {
    return await task()
  } catch {
    await wait(350)
    return task()
  }
}

export function hasPromptTemplateLeakage(text) {
  // Detects leaked prompt-template/system markers so raw scaffolding is not shown as assistant output.
  const blockedMarkers = [
    'you are a json api assistant',
    'user prompt:',
    'context json:',
    'required response schema:',
    'user response:'
  ]

  const normalized = String(text || '').toLowerCase()
  return blockedMarkers.some((marker) => normalized.includes(marker))
}

export function readAssistantText(aiPayload) {
  // Extracts the first safe, non-empty assistant string across known backend payload shapes.
  const candidateValues = [
    aiPayload?.assistant_text,
    aiPayload?.result,
    aiPayload?.answer,
    aiPayload?.response?.summary,
    aiPayload?.response,
    aiPayload?.summary,
    typeof aiPayload === 'string' ? aiPayload : ''
  ]

  for (const value of candidateValues) {
    if (typeof value !== 'string') continue
    const cleaned = value.trim()
    if (!cleaned) continue
    if (hasPromptTemplateLeakage(cleaned)) return ''
    return cleaned
  }

  return ''
}

export function buildFirstChatTitle(cleanPrompt, fallbackIndex) {
  // Generates a short default chat title from the opening prompt with a stable fallback label.
  return cleanPrompt.trim().split(/\s+/).filter(Boolean).slice(0, 3).join(' ') || `New Chat ${fallbackIndex}`
}

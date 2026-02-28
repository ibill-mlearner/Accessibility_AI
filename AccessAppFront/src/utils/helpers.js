export function createId() {
  return Date.now() + Math.floor(Math.random() * 1000)
  // need a better idea for this
}

export function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function withSingleRetry(task) {
  try {
    return await task()
  } catch {
    await wait(350)
    return task()
  }
}

export function hasPromptTemplateLeakage(text) {
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
  return cleanPrompt.trim().split(/\s+/).filter(Boolean).slice(0, 3).join(' ') || `New Chat ${fallbackIndex}`
}
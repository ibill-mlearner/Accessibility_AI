/** Timeline adapters for converting backend message/interaction payloads into chat-turn rows. */
export function parseTimelineTimestamp(value, fallbackIndex = 0) {
  // Parses server timestamp values and provides a deterministic fallback ordering timestamp when missing.
  const parsed = Date.parse(value || '')
  return Number.isNaN(parsed) ? Number.MAX_SAFE_INTEGER - (100000 - fallbackIndex) : parsed
}

export function buildTimelineFromInteractions(interactions = []) {
  // Expands interaction records into alternating user/assistant turns while preserving source order metadata.
  const turns = []
  interactions.forEach((interaction, index) => {
    const interactionId = interaction?.id ?? `unknown-${index}`
    const createdAt = interaction?.created_at || null
    const promptText = String(interaction?.prompt || '').trim()
    const assistantText = String(interaction?.response_text || '').trim()

    if (promptText) turns.push({ id: `interaction-${interactionId}-user`, role: 'user', text: promptText, createdAt, order: index * 2 })
    if (assistantText) turns.push({ id: `interaction-${interactionId}-assistant`, role: 'assistant', text: assistantText, createdAt, order: index * 2 + 1 })
  })

  return turns
}

export function buildTimelineFromMessages(messages = []) {
  // Adapts legacy flat message arrays into timeline turn objects with inferred role sequencing.
  return messages.map((message, index) => ({
    id: message.id,
    role: index % 2 === 0 ? 'user' : 'assistant',
    text: String(message?.message_text || '').trim(),
    createdAt: null,
    order: index
  }))
}

export function normalizeTimeline(interactions = [], messages = []) {
  // Chooses the best source dataset, removes empty text, sorts deterministically, and returns render-ready turns.
  const source = interactions.length ? buildTimelineFromInteractions(interactions) : buildTimelineFromMessages(messages)
  return source
    .filter((message) => Boolean(message.text))
    .sort((a, b) => {
      const aTime = parseTimelineTimestamp(a.createdAt, a.order)
      const bTime = parseTimelineTimestamp(b.createdAt, b.order)
      if (aTime !== bTime) return aTime - bTime
      return (a.order ?? 0) - (b.order ?? 0)
    })
    .map(({ id, role, text }) => ({ id, role, text }))
}

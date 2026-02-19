export function sortedByStableKey(items) {
  return [...items].sort((a, b) => {
    const aKey = a.createdAt || a.start || a.id || Number.MAX_SAFE_INTEGER
    const bKey = b.createdAt || b.start || b.id || Number.MAX_SAFE_INTEGER
    if (aKey < bKey) return -1
    if (aKey > bKey) return 1
    return 0
  })
}

export function deriveSelectedId(previousId, items) {
  if (!items?.length) return null
  if (previousId !== null && items.some((item) => item.id === previousId)) return previousId
  return sortedByStableKey(items)[0]?.id ?? items[0]?.id ?? null
}
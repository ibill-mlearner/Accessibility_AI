/** Selection utilities for stable list ordering and safe selected-id fallback behavior. */
export function sortedByStableKey(items) {
  // Sorts records by a stable timestamp/id key so fallback selections do not jump unpredictably.
  return [...items].sort((leftRecord, rightRecord) => {
    const leftSortKey = leftRecord.createdAt || leftRecord.start || leftRecord.id || Number.MAX_SAFE_INTEGER
    const rightSortKey = rightRecord.createdAt || rightRecord.start || rightRecord.id || Number.MAX_SAFE_INTEGER
    if (leftSortKey < rightSortKey) return -1
    if (leftSortKey > rightSortKey) return 1
    return 0
  })
}

export function deriveSelectedId(previousId, items) {
  // Preserves prior selection when valid, otherwise chooses a deterministic first available record id.
  if (!items?.length) return null
  if (previousId !== null && items.some((item) => item.id === previousId)) return previousId
  return sortedByStableKey(items)[0]?.id ?? items[0]?.id ?? null
}

/** Utilities for splitting profile-scoped accessibility features from site-wide feature toggles. */
const PROFILE_PREFIX = 'profile:'
const LEGACY_PROFILE_PREFIX = 'standard;'

function normalizedText(value) {
  // Normalizes any feature text field for prefix checks regardless of casing/whitespace.
  return String(value || '').trim().toLowerCase()
}

export function isProfileScopedFeature(feature = {}) {
  // Detects profile-only features based on naming conventions used in feature title/details fields.
  const title = normalizedText(feature?.title || feature?.name)
  const details = normalizedText(feature?.details)
  return title.startsWith(PROFILE_PREFIX) || details.startsWith(LEGACY_PROFILE_PREFIX)
}

export function filterSiteWideFeatures(features = []) {
  // Returns only features intended for global/site-wide toggles (excludes profile-scoped entries).
  return features.filter((feature) => !isProfileScopedFeature(feature))
}

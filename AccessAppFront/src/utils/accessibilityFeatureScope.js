const PROFILE_PREFIX = 'profile:'
const LEGACY_PROFILE_PREFIX = 'standard;'

function normalizedText(value) {
  return String(value || '').trim().toLowerCase()
}

export function isProfileScopedFeature(feature = {}) {
  const title = normalizedText(feature?.title || feature?.name)
  const details = normalizedText(feature?.details)
  return title.startsWith(PROFILE_PREFIX) || details.startsWith(LEGACY_PROFILE_PREFIX)
}

export function filterSiteWideFeatures(features = []) {
  return features.filter((feature) => !isProfileScopedFeature(feature))
}


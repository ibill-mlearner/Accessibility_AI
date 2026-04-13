import { computed, ref } from 'vue'

/**
 * Minimal FontFace loader for a small, fixed set of custom fonts.
 *
 * Usage:
 * const { isSupported, loadedFonts, loadFonts } = useFontFaceLoader()
 * await loadFonts([
 *   { family: 'OpenDyslexic', source: 'url("/fonts/OpenDyslexic-Regular.woff2") format("woff2")' },
 *   { family: 'Atkinson Hyperlegible', source: 'url("/fonts/AtkinsonHyperlegible-Regular.woff2") format("woff2")' }
 * ])
 */
export function useFontFaceLoader() {
  const loadedFonts = ref([])
  const isLoading = ref(false)

  const isSupported = computed(() => (
    typeof window !== 'undefined'
    && typeof FontFace === 'function'
    && typeof document !== 'undefined'
    && Boolean(document.fonts)
  ))

  async function loadFonts(fontSpecs = []) {
    if (!isSupported.value) return []
    if (!Array.isArray(fontSpecs) || !fontSpecs.length) {
      loadedFonts.value = []
      return []
    }

    isLoading.value = true

    const results = await Promise.all(fontSpecs.map(async (spec = {}) => {
      const family = String(spec.family || '').trim()
      const source = String(spec.source || '').trim()

      if (!family || !source) {
        return { family, status: 'error', loaded: false, reason: 'missing-family-or-source' }
      }

      const descriptors = spec.descriptors && typeof spec.descriptors === 'object'
        ? spec.descriptors
        : undefined

      try {
        const fontFace = new FontFace(family, source, descriptors)
        await fontFace.load()
        document.fonts.add(fontFace)
        await fontFace.loaded

        return {
          family: fontFace.family,
          status: fontFace.status,
          loaded: fontFace.status === 'loaded'
        }
      } catch (error) {
        return {
          family,
          status: 'error',
          loaded: false,
          reason: error?.message || 'font-load-failed'
        }
      }
    }))

    loadedFonts.value = results
    isLoading.value = false
    return results
  }

  return {
    isSupported,
    isLoading,
    loadedFonts,
    loadFonts
  }
}

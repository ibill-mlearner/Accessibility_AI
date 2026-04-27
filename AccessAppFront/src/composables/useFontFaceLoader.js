import { computed, ref } from 'vue'

/**
 * Minimal FontFace loader for a small, fixed set of custom fonts.
 * Handoff note: this remains partially reliable across environments and should be treated as best-effort for now.
 *
 * Usage:
 * const { isSupported, loadedFonts, loadFonts } = useFontFaceLoader()
 * await loadFonts([
 *   { family: 'OpenDyslexic', source: 'url("/fonts/OpenDyslexic-Regular.woff2") format("woff2")' },
 *   { family: 'Atkinson Hyperlegible', source: 'url("/fonts/AtkinsonHyperlegible-Regular.woff2") format("woff2")' }
 * ])
 */
export function useFontFaceLoader() {
  // Stores per-font load outcomes so UI can report which families are actually active.
  const loadedFonts = ref([])
  // Exposes in-flight state for UI controls while font assets are resolving.
  const isLoading = ref(false)

  // Indicates browser/runtime support for dynamic FontFace loading APIs.
  const isSupported = computed(() => (
    typeof window !== 'undefined'
    && typeof FontFace === 'function'
    && typeof document !== 'undefined'
    && Boolean(document.fonts)
  ))

  // Attempts to load requested font specs and returns success/error status per item.
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

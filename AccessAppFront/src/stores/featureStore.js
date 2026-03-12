import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { toResourceError } from '../stores/helpers/apiErrors'

function normalizeFeature(feature = {}) {
  return {
    ...feature,
    active: Boolean(feature.active),
    enabled: Boolean(feature.enabled)
  }
}

export const useFeatureStore = defineStore('features', {
  state: () => ({
    features: [],
    selectedAccessibilityLinkIds: [],
    actionStatus: {}
  }),
  getters: {
    selectedLinkIds(state) {
      return state.selectedAccessibilityLinkIds.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
    }
  },
  actions: {
    async fetchFeatures() {
      const key = 'fetchFeatures'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const [featuresResponse, preferencesResponse] = await Promise.all([
          api.get('/api/v1/features'),
          api.get('/api/v1/features/preferences')
        ])
        const records = Array.isArray(featuresResponse?.data) ? featuresResponse.data : []
        const preferences = Array.isArray(preferencesResponse?.data) ? preferencesResponse.data : []
        const enabledById = new Map(
          preferences
            .map((entry) => [Number(entry?.accommodation_id), Boolean(entry?.enabled)])
            .filter(([id]) => Number.isInteger(id) && id > 0)
        )

        this.features = records.map((feature) => normalizeFeature({
          ...feature,
          enabled: enabledById.has(Number(feature?.id))
            ? enabledById.get(Number(feature?.id))
            : Boolean(feature?.enabled)
        }))
        this.setSelectedAccessibilityLinkIds(
          this.features.filter((feature) => feature.enabled).map((feature) => feature.id)
        )
        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
      } catch (error) {
        const wrapped = toResourceError(error, {
          resourceLabel: 'features',
          unavailableMessage: 'Features endpoint is unavailable. Enable /api/v1/features or disable feature toggles.',
          fallbackMessage: 'Unable to load accessibility features.'
        })
        setActionError(this.actionStatus, key, wrapped.message)
        throw wrapped
      }
    },
    async updateFeaturePreference(featureId, enabled) {
      const key = `updateFeaturePreference:${featureId}`
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })
      try {
        const response = await api.patch(`/api/v1/features/preferences/${featureId}`, {
          enabled: Boolean(enabled)
        })
        const updatedEnabled = Boolean(response?.data?.enabled)
        this.features = this.features.map((item) => (
          item.id === featureId ? { ...item, enabled: updatedEnabled } : item
        ))

        const selectedSet = new Set(this.selectedLinkIds)
        if (updatedEnabled) selectedSet.add(Number(featureId))
        else selectedSet.delete(Number(featureId))
        this.setSelectedAccessibilityLinkIds(Array.from(selectedSet))

        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return updatedEnabled
      } catch {
        setActionError(this.actionStatus, key, 'Unable to update accessibility feature preference.')
        throw new Error('Unable to update accessibility feature preference.')
      }
    },
    setSelectedAccessibilityLinkIds(linkIds = []) {
      let normalIds = []

      if (Array.isArray(linkIds)) {
        normalIds = linkIds.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
      }
      this.selectedAccessibilityLinkIds = Array.from(new Set(normalIds))
    }

  }
})

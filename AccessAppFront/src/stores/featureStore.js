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
    resetFeatureState() {
      this.features = []
      this.selectedAccessibilityLinkIds = []
      this.actionStatus = {}
    },
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
    async replaceFeaturePreferences(preferences = []) {
      const key = 'replaceFeaturePreferences'
      setActionStatus(this.actionStatus, key, { loading: true, error: '' })

      try {
        const normalized = preferences
          .map((entry) => ({
            accommodation_id: Number(entry?.accommodation_id),
            enabled: Boolean(entry?.enabled)
          }))
          .filter((entry) => Number.isInteger(entry.accommodation_id) && entry.accommodation_id > 0)

        const response = await api.put('/api/v1/features/preferences', {
          preferences: normalized
        })

        const updated = Array.isArray(response?.data) ? response.data : normalized
        const enabledById = new Map(
          updated
            .map((entry) => [Number(entry?.accommodation_id), Boolean(entry?.enabled)])
            .filter(([id]) => Number.isInteger(id) && id > 0)
        )

        this.features = this.features.map((item) => (
          enabledById.has(Number(item.id))
            ? { ...item, enabled: Boolean(enabledById.get(Number(item.id))) }
            : item
        ))
        this.setSelectedAccessibilityLinkIds(
          this.features
            .filter((feature) => feature.enabled)
            .map((feature) => feature.id)
        )

        setActionStatus(this.actionStatus, key, { loading: false, error: '' })
        return updated
      } catch {
        setActionError(this.actionStatus, key, 'Unable to replace accessibility feature preferences.')
        throw new Error('Unable to replace accessibility feature preferences.')
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

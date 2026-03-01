import { defineStore } from 'pinia'
import api from '../services/api'
import { setActionStatus, setActionError } from '../stores/helpers/actionStatus'
import { toResourceError } from '../stores/helpers/apiErrors'

function normalizeFeature(feature = {}) {
    return {
        ...feature,
        active: Boolean(feature.active ?? feature.enabled)
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
            return state.selectedAccessibilityLinkIds.map( (id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
        }
    },
    actions: {
    async fetchFeatures() {
        const key = 'fetchFeatures'
        setActionStatus(this.actionStatus, key, { loading: true, error: '' })
        try {
            const response = await api.get('/api/v1/features')
            const records = Array.isArray(response?.data) ? response.data : []
            this.features = records.map(normalizeFeature)
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
    async updateFeature(featureId, patch) {
        const key = `updateFeature:${featureId}`
        setActionStatus(this.actionStatus, key, { loading: true, error: '' })
        try {
            const existing = this.features.find((item) => item.id === featureId) || {}
            const payload = {
                ...existing,
                ...patch,
                active: Boolean((patch?.active ?? patch?.enabled) ?? existing.active)
        }
            const response = await api.patch(`/api/v1/features/${featureId}`, payload)
            const normalized = normalizeFeature(response?.data || payload)
            this.features = this.features.map((item) => (item.id === featureId ? normalized : item))
            setActionStatus(this.actionStatus, key, { loading: false, error: '' })
            return normalized
        } catch {
            setActionError(this.actionStatus, key, 'Unable to update accessibility feature.')
            throw new Error('Unable to update accessibility feature.')
        }
    },
    setSelectedAccessibilityLinkIds(linkIds = []) {
        let normalIds = []

        if (Array.isArray(linkIds)) {
            normalIds = linkIds.map( (id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
        }
        this.selectedAccessibilityLinkIds = Array.from(new Set(normalIds))

    }
    
}})

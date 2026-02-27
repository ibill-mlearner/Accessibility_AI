<template>
  <section class="d-flex flex-column gap-3">
    <p v-if="!fstore.features.length" class="text-muted mb-2">
      No accessibility features available right now.
    </p>
    <FeatureOptionCard
      v-for="feature in fstore.features"
      :key="feature.id"
      :item="feature"
      @toggle="setFeatureEnabled(feature, $event)"
    />
  </section>
</template>

<script setup>
// import { useAppStore } from '../stores/appStore'
import { useAuthStore } from '../stores/authStore'
import { useFeatureStore } from '../stores/featureStore'
import FeatureOptionCard from '../components/classes/FeatureOptionCard.vue'

// const store = useAppStore()
// Development-only API trigger logging for integration debugging.
// TODO(v1.0): Remove console logging before release.

const fstore = useFeatureStore()
const auth = useAuthStore()

function setFeatureEnabled(feature, enabled) {
  console.info('[API trigger] updateFeature', {
    actor: auth.role,
    why: 'User toggled an accessibility feature option.',
    featureId: feature.id,
    featureTitle: feature.title,
    enabled
  })

  fstore.updateFeature(feature.id, { active: enabled })
}
</script>

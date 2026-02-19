<template>
  <section class="d-flex flex-column gap-3">
    <FeatureOptionCard
      v-for="feature in store.features"
      :key="feature.id"
      :item="feature"
      @toggle="setFeatureEnabled(feature, $event)"
    />
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
import FeatureOptionCard from '../components/classes/FeatureOptionCard.vue'

const store = useAppStore()
// Development-only API trigger logging for integration debugging.
// TODO(v1.0): Remove console logging before release.

function setFeatureEnabled(feature, enabled) {
  console.info('[API trigger] updateFeature', {
    actor: store.role,
    why: 'User toggled an accessibility feature option.',
    featureId: feature.id,
    featureTitle: feature.title,
    enabled
  })

  store.updateFeature(feature.id, { enabled })
}
</script>

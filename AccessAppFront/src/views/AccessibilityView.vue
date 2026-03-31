<template>
  <section class="accessibility-thread d-flex flex-column gap-2">
    <div class="accessibility-thread__features overflow-auto">
      <div class="d-flex flex-column gap-3">
        <p v-if="!fstore.features.length" class="text-muted mb-2">
          No accessibility features available right now.
        </p>
        <FeatureOptionCard
          v-for="feature in fstore.features"
          :key="feature.id"
          :item="feature"
          @toggle="setFeatureEnabled(feature, $event)"
        />
      </div>
    </div>

    <div
      class="accessibility-thread__composer-spacer"
      aria-hidden="true"
    />
  </section>
</template>

<script setup>
import { useAuthStore } from '../stores/authStore'
import { useFeatureStore } from '../stores/featureStore'
import FeatureOptionCard from '../components/classes/FeatureOptionCard.vue'

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
  fstore.updateFeaturePreference(feature.id, enabled)
}
</script>

<style scoped>
.accessibility-thread {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.accessibility-thread__features {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.accessibility-thread__composer-spacer {
  flex: 0 0 auto;
  height: 86px;
  opacity: 0;
  pointer-events: none;
}
</style>

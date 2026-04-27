<template>
  <section class="accessibility-thread d-flex flex-column gap-2">
    <div class="accessibility-thread__features overflow-auto">
      <div class="d-flex flex-column gap-3">
        <p v-if="!visibleSiteWideFeatures.length" class="text-muted mb-2">
          No accessibility features available right now.
        </p>
        <FeatureOptionCard
          v-for="feature in visibleSiteWideFeatures"
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
// Accessibility view presents only site-wide (non-profile) feature toggles.
import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useFeatureStore } from '../stores/featureStore'
import FeatureOptionCard from '../components/classes/FeatureOptionCard.vue'
import { filterSiteWideFeatures } from '../utils/accessibilityFeatureScope'

const fstore = useFeatureStore()
const auth = useAuthStore()
// Keeps view list limited to globally applicable feature toggles.
const visibleSiteWideFeatures = computed(() =>
  filterSiteWideFeatures(fstore.features)
)

function setFeatureEnabled(feature, enabled) {
  // Delegates toggle persistence to the feature store and logs intent for traceability.
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

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../styles/views/accessibility-view.css"></style>

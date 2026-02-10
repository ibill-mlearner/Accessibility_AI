<template>
  <section class="cards">
    <FeatureOptionCard :item="enabledFeature" />
    <FeatureOptionCard :item="disabledFeature" />
  </section>
</template>

<script setup>
import FeatureOptionCard from '../../components/classes/FeatureOptionCard.vue'

const enabledFeature = {
  id: 1,
  title: 'Note Taking assistance',
  description: 'Feature enabled preview',
  enabled: true
}

const disabledFeature = {
  id: 2,
  title: 'Summarization and restating',
  description: 'Feature disabled preview',
  enabled: false
}
</script>

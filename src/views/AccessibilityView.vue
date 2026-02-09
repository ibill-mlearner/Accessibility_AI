<template>
  <section class="cards">
    <FeatureOptionCard v-for="feature in store.features" :key="feature.id" :item="feature" />
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
import FeatureOptionCard from '../components/classes/FeatureOptionCard.vue'

const store = useAppStore()
</script>

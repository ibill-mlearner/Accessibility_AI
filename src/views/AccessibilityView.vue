<template>
  <section class="cards">
    <article v-for="feature in store.features" :key="feature.id" class="card-row">
      <div>
        <p>{{ feature.description }}</p>
        <label>
          <input type="radio" name="feature" :checked="feature.enabled" />
          {{ feature.title }}
        </label>
      </div>
    </article>
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
const store = useAppStore()
</script>

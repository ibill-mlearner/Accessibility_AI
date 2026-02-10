<template>
  <section class="cards">
    <OptionSelector label="Radio selector preview" :checked="true" name="preview" @change="changed = true" />
    <OptionSelector type="checkbox" label="Checkbox selector preview" :checked="false" name="preview-checkbox" />
    <p>Changed: {{ changed }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import OptionSelector from '../../components/ui/OptionSelector.vue'

const changed = ref(false)
</script>

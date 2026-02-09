<template>
  <section>
    <ClassOptionCard :item="item" :checked="checked" action-label="Instructor/contact" @select="onSelect" />
    <p>Selected class id: {{ selectedId }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import ClassOptionCard from '../../components/classes/ClassOptionCard.vue'

const item = {
  id: 101,
  name: 'Preview Biology 103',
  description: 'Class option preview description.'
}

const checked = ref(true)
const selectedId = ref(null)

function onSelect(id) {
  selectedId.value = id
}
</script>

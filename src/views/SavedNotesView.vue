<template>
  <section class="cards">
    <SavedNoteCard v-for="note in store.notes" :key="note.id" :note="note" />
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
import SavedNoteCard from '../components/notes/SavedNoteCard.vue'

const store = useAppStore()
</script>

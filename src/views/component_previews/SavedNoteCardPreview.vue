<template>
  <section>
    <SavedNoteCard :note="note" />
  </section>
</template>

<script setup>
import SavedNoteCard from '../../components/notes/SavedNoteCard.vue'

const note = {
  id: 1,
  class: 'Bio',
  date: '2026-02-09',
  chat: 'Preview Chat',
  content: 'Saved note preview content . . .'
}
</script>

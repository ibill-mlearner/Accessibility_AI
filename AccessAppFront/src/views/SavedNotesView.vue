<template>
  <section class="d-flex flex-column gap-3">
    <SavedNoteCard v-for="note in noteStore.notes" :key="note.id" :note="note" @delete="handleDeleteNote" />
  </section>
</template>

<script setup>
import { useAuthStore } from '../stores/authStore'
import { useNoteStore } from '../stores/noteStore'
import SavedNoteCard from '../components/notes/SavedNoteCard.vue'

const authStore = useAuthStore()
const noteStore = useNoteStore()
// Development-only API trigger logging for integration debugging.
// TODO(v1.0): Remove console logging before release.

function handleDeleteNote(noteId) {
  const note = noteStore.notes.find((item) => item.id === noteId)
  console.info('[API trigger] deleteNote', {
    actor: authStore.role,
    why: 'User clicked Delete Note from a saved note card.',
    noteId,
    noteChatTitle: note?.chat || '',
    className: note?.class || ''
  })

  noteStore.deleteNote(noteId)
}
</script>

<template>
  <section class="d-flex flex-column gap-3">
    <SavedNoteCard v-for="note in store.notes" :key="note.id" :note="note" @delete="handleDeleteNote" />
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
import SavedNoteCard from '../components/notes/SavedNoteCard.vue'

const store = useAppStore()
// Development-only API trigger logging for integration debugging.
// TODO(v1.0): Remove console logging before release.

function handleDeleteNote(noteId) {
  const note = store.notes.find((item) => item.id === noteId)
  console.info('[API trigger] deleteNote', {
    actor: store.role,
    why: 'User clicked Delete Note from a saved note card.',
    noteId,
    noteChatTitle: note?.chat || '',
    className: note?.class || ''
  })

  store.deleteNote(noteId)
}
</script>

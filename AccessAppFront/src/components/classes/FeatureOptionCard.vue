<template>
  <article class="card shadow-sm">
    <div class="card-body row g-3">
      <aside class="col-12 col-lg-4">
        <p class="mb-1">Saved for class: {{ note.class }}</p>
        <p class="mb-1">Saved on: {{ note.date }}</p>
        <p class="mb-1">Chat title: {{ note.chat }}</p>
      </aside>
      <div class="col-12 col-lg-8 d-flex flex-column gap-2">
        <ChatBubbleCard :text="note.content" />
        <div class="d-flex justify-content-between gap-2">
          <button class="btn btn-outline-secondary">Read Aloud</button>
          <button class="btn btn-outline-danger" @click="$emit('delete', note.id)">Delete Note</button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import OptionCard from '../ui/OptionCard.vue'
import OptionSelector from '../ui/OptionSelector.vue'

defineProps({
  item: { type: Object, required: true },
  name: { type: String, default: 'feature' }
})

defineEmits(['toggle'])
</script>

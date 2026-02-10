<template>
  <article class="saved-note">
    <aside>
      <p>Saved for class: {{ note.class }}</p>
      <p>Saved on: {{ note.date }}</p>
      <p>Chat title: {{ note.chat }}</p>
    </aside>
    <div>
      <ChatBubbleCard :text="note.content" />
      <div class="button-row">
        <button class="btn">Read Aloud</button>
        <button class="btn">Save as Note</button>
      </div>
    </div>
  </article>
</template>

<script setup>
import ChatBubbleCard from '../chat/ChatBubbleCard.vue'

defineProps({
  note: {
    type: Object,
    required: true
  }
})
</script>

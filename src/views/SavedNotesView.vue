<template>
  <section class="cards">
    <article v-for="note in store.notes" :key="note.id" class="saved-note">
      <aside>
        <p>Saved for class: {{ note.class }}</p>
        <p>Saved on: {{ note.date }}</p>
        <p>Chat title: {{ note.chat }}</p>
      </aside>
      <div>
        <div class="panel">{{ note.content }}</div>
        <div class="button-row">
          <button class="btn">Read Aloud</button>
          <button class="btn">Save as Note</button>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { useAppStore } from '../stores/appStore'
const store = useAppStore()
</script>

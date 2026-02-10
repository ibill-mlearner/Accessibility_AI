<template>
  <section class="cards">
    <ChatBubbleCard text="System preview response . . ." variant="system" />
    <ChatBubbleCard text="User preview prompt . . ." variant="user" :show-actions="true" />
  </section>
</template>

<script setup>
import ChatBubbleCard from '../../components/chat/ChatBubbleCard.vue'
</script>

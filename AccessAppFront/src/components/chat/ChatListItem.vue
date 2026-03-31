<template>
  <li
    class="chat-list-item list-group-item p-0"
    :class="{ 'bg-purple-200': isActive }"
  >
    <div class="chat-list-item__container d-flex align-items-center gap-2 px-2 py-1">
      <button
        class="chat-list-item__title flex-grow-1 text-start border-0 bg-transparent px-2 py-1"
        type="button"
        @click="$emit('select', chat.id)"
      >
        {{ chat.title }}
      </button>

      <div class="dropdown chat-list-item__menu">
        <button
          :id="dropdownId"
          class="btn btn-sm btn-outline-secondary border-0"
          type="button"
          data-bs-toggle="dropdown"
          aria-expanded="false"
          aria-label="Chat options"
          @click.stop
        >
          <span aria-hidden="true">⋯</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end" :aria-labelledby="dropdownId">
          <li>
            <p class="dropdown-item-text mb-1 text-muted small">
              Temporary demo options. These items show where future chat actions can live.
            </p>
          </li>
          <li><span class="dropdown-item-text">Edit</span></li>
          <li><span class="dropdown-item-text">Archive</span></li>
          <li><hr class="dropdown-divider" /></li>
          <li><span class="dropdown-item-text text-danger">Delete</span></li>
        </ul>
      </div>
    </div>
  </li>
</template>

<script setup>
defineProps({
  chat: {
    type: Object,
    required: true
  },
  isActive: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select'])

const dropdownId = `chat-item-options-${Math.random().toString(36).slice(2, 10)}`
</script>

<style scoped>
.chat-list-item__container {
  min-height: 2.5rem;
}

.chat-list-item__title {
  border-radius: 0.375rem;
}

.chat-list-item__title:hover,
.chat-list-item__title:focus-visible {
  background-color: rgba(0, 0, 0, 0.05) !important;
  outline: none;
}

.chat-list-item__menu {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.chat-list-item:hover .chat-list-item__menu,
.chat-list-item:focus-within .chat-list-item__menu,
.chat-list-item.bg-purple-200 .chat-list-item__menu {
  opacity: 1;
  pointer-events: auto;
}
</style>

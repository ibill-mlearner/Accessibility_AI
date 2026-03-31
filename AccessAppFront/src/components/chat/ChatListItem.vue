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

      <button
        ref="menuButtonRef"
        class="chat-list-item__menu-button btn btn-sm btn-outline-secondary border-0"
        type="button"
        aria-label="Chat options"
        :aria-expanded="String(isMenuOpen)"
        @click.stop="toggleMenu"
      >
        <span aria-hidden="true">⋯</span>
      </button>
    </div>

    <Teleport to="body">
      <ul
        v-if="isMenuOpen"
        ref="menuRef"
        class="dropdown-menu chat-list-item__floating-menu show"
        role="menu"
        :style="floatingMenuStyle"
      >
        <!-- Temporary demo options: placeholder location for future chat actions. -->
        <li><span class="dropdown-item-text">Edit</span></li>
        <li><span class="dropdown-item-text">Archive</span></li>
        <li><hr class="dropdown-divider" /></li>
        <li><span class="dropdown-item-text text-danger">Delete</span></li>
      </ul>
    </Teleport>
  </li>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

// TODO(ui-refactor): Extract floating chat-menu state/position/close behavior into a reusable composable
// (e.g., useFloatingChatMenu) so this component stays focused on rendering.
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

const menuButtonRef = ref(null)
const menuRef = ref(null)
const isMenuOpen = ref(false)
const menuPosition = ref({ top: 0, left: 0 })

const floatingMenuStyle = computed(() => ({
  position: 'fixed',
  top: `${menuPosition.value.top}px`,
  left: `${menuPosition.value.left}px`,
  zIndex: 2000
}))

// TODO(ui-refactor): Move these menu lifecycle + positioning handlers into the composable noted above.
function updateMenuPosition() {
  if (!menuButtonRef.value) return
  const rect = menuButtonRef.value.getBoundingClientRect()
  menuPosition.value = {
    top: rect.bottom + 4,
    left: Math.max(8, rect.right - 180)
  }
}

function closeMenu() {
  isMenuOpen.value = false
}

function toggleMenu() {
  if (isMenuOpen.value) {
    closeMenu()
    return
  }

  updateMenuPosition()
  isMenuOpen.value = true
  nextTick(() => updateMenuPosition())
}

function handleGlobalClick(event) {
  if (!isMenuOpen.value) return
  if (menuRef.value?.contains(event.target) || menuButtonRef.value?.contains(event.target)) return
  closeMenu()
}

function handleEscape(event) {
  if (event.key === 'Escape') {
    closeMenu()
  }
}

function handleViewportChange() {
  if (!isMenuOpen.value) return
  updateMenuPosition()
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick, true)
  window.addEventListener('keydown', handleEscape)
  window.addEventListener('resize', handleViewportChange)
  window.addEventListener('scroll', handleViewportChange, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick, true)
  window.removeEventListener('keydown', handleEscape)
  window.removeEventListener('resize', handleViewportChange)
  window.removeEventListener('scroll', handleViewportChange, true)
})
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

.chat-list-item__menu-button {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.chat-list-item:hover .chat-list-item__menu-button,
.chat-list-item:focus-within .chat-list-item__menu-button,
.chat-list-item.bg-purple-200 .chat-list-item__menu-button,
.chat-list-item__menu-button[aria-expanded='true'] {
  opacity: 1;
  pointer-events: auto;
}

.chat-list-item__floating-menu {
  min-width: 11.25rem;
}
</style>

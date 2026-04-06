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

<style scoped src="../../styles/components/chat/chat-list-item.css"></style>

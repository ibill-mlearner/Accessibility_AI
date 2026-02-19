<template>
  <section class="d-flex flex-column gap-3">
    <div class="btn-group" role="group" aria-label="Role picker">
      <button class="btn btn-outline-secondary" @click="store.setRole('student')">Student</button>
      <button class="btn btn-outline-secondary" @click="store.setRole('instructor')">Instructor</button>
    </div>

    <ClassOptionCard
      v-for="item in store.roleClasses"
      :key="item.id"
      :item="item"
      :checked="item.id === store.selectedClassId"
      :action-label="store.role === 'instructor' ? 'Class instructions' : 'Instructor/contact'"
      @select="store.selectedClassId = $event"
    />
  </section>
</template>

<script setup>
import { watchEffect } from 'vue'
import { useAppStore } from '../stores/appStore'
import ClassOptionCard from '../components/classes/ClassOptionCard.vue'

const props = defineProps({ role: String })
const store = useAppStore()

watchEffect(() => {
  if (props.role === 'student' || props.role === 'instructor') {
    store.setRole(props.role)
  }
})
</script>

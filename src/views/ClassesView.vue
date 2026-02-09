<template>
  <section class="cards">
    <div class="role-picker">
      <button class="btn" @click="store.setRole('student')">Student</button>
      <button class="btn" @click="store.setRole('instructor')">Instructor</button>
    </div>

    <article v-for="item in store.roleClasses" :key="item.id" class="card-row">
      <div>
        <p>{{ item.description }}</p>
        <label>
          <input type="radio" name="class" :checked="item.id === store.selectedClassId" @change="store.selectedClassId = item.id" />
          {{ item.name }}
        </label>
      </div>
      <button class="btn">{{ store.role === 'instructor' ? 'Class instructions' : 'Instructor/contact' }}</button>
    </article>
  </section>
</template>

<script setup>
import { watchEffect } from 'vue'
import { useAppStore } from '../stores/appStore'

const props = defineProps({ role: String })
const store = useAppStore()

watchEffect(() => {
  if (props.role === 'student' || props.role === 'instructor') {
    store.setRole(props.role)
  }
})
</script>

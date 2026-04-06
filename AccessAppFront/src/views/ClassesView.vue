<template>
  <section class="classes-view d-flex flex-column gap-3">
    <header class="card shadow-sm">
      <div class="card-body">
        <h2 class="h4 mb-1">Classes</h2>
        <p class="text-muted mb-0">{{ roleSummary }}</p>
      </div>
    </header>

    <p v-if="fetchError" class="alert alert-danger mb-0">{{ fetchError }}</p>

    <section class="card shadow-sm">
      <div class="card-body">
        <h3 class="h5 mb-0">Available classes</h3>
      </div>
    </section>

    <section class="d-flex flex-column gap-2">
      <p v-if="fetchLoading" class="text-muted mb-0">Loading classes . . .</p>
      <p v-else-if="!classStore.roleClasses.length" class="text-muted mb-0">No classes found for your role.</p>

      <ClassOptionCard
        v-for="item in classStore.roleClasses"
        :key="item.id"
        :item="item"
        :checked="item.id === classStore.selectedClassId"
        @select="classStore.setSelectedClassId($event)"
      />
    </section>

    <ClassDetailsEditor
      v-if="canEditClass"
      :selected-class="classStore.selectedClass"
      :can-edit="canEditClass"
      :is-admin="canCreateClass"
      :instructors="classStore.instructors"
      :is-saving="updateLoading"
      @save="handleUpdateClass"
    />

    <p v-if="updateError" class="alert alert-warning mb-0">{{ updateError }}</p>

    <ClassAdminActions
      :selected-class="classStore.selectedClass"
      :can-create="canCreateClass"
      :can-delete="canDeleteClass"
      :instructors="classStore.instructors"
      :is-submitting="createLoading || deleteLoading"
      @create="handleCreateClass"
      @delete="handleDeleteClass"
    />

    <p v-if="createError" class="alert alert-warning mb-0">{{ createError }}</p>
    <p v-if="deleteError" class="alert alert-warning mb-0">{{ deleteError }}</p>
  </section>
</template>

<script setup>
import { useAuthStore } from '../stores/authStore'
import { useClassStore } from '../stores/classStore'
import { useClassesViewState } from '../composables/useClassesViewState'
import ClassOptionCard from '../components/classes/ClassOptionCard.vue'
import ClassDetailsEditor from '../components/classes/ClassDetailsEditor.vue'
import ClassAdminActions from '../components/classes/ClassAdminActions.vue'

const auth = useAuthStore()
const classStore = useClassStore()

const {
  canEditClass,
  canCreateClass,
  canDeleteClass,
  roleSummary,
  fetchLoading,
  fetchError,
  updateLoading,
  updateError,
  deleteLoading,
  deleteError,
  createLoading,
  createError,
  handleCreateClass,
  handleUpdateClass,
  handleDeleteClass
} = useClassesViewState({ auth, classStore })
</script>

<style scoped src="../styles/views/classes-view.css"></style>

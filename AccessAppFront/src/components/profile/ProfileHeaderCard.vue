<template>
  <section class="card bg-light-subtle border-0 profile-header-card">
    <div class="card-body">
      <h3 class="h6 text-uppercase text-muted mb-3">Account</h3>
      <dl class="row mb-0">
        <dt class="col-sm-3">Status</dt>
        <dd class="col-sm-9">{{ isAuthenticated ? 'Signed in' : 'Not signed in' }}</dd>

        <dt class="col-sm-3">Email</dt>
        <dd class="col-sm-9">{{ user?.email || 'Unknown email' }}</dd>

        <dt class="col-sm-3">Role</dt>
        <dd class="col-sm-9 text-capitalize">{{ role || 'unknown' }}</dd>

        <dt class="col-sm-3">User ID</dt>
        <dd class="col-sm-9">{{ user?.id || 'Unavailable' }}</dd>
      </dl>
    </div>
  </section>
</template>

<script setup>
defineProps({
  user: { type: Object, default: null },
  role: { type: String, default: 'guest' },
  isAuthenticated: { type: Boolean, default: false }
})
</script>

<style scoped src="../../styles/components/profile/profile-header-card.css"></style>

<template>
  <!-- Fallback route-level error panel for unknown paths or unrecoverable navigation states. -->
  <section class="card shadow-sm text-center error-view">
    <img src="/logo.svg" alt="logo" class="error-view__logo mx-auto mb-3"/>
    <h2 class="display-6">AI Project or Logo</h2>
    <p class="lead">40X: Page error please refer to the project owner</p>
  </section>
</template>

<!-- Styles are centralized under src/styles so component/view files keep behavior separate from presentation concerns. -->
<style scoped src="../styles/views/error-view.css"></style>

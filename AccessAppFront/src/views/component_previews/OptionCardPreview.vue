<template>
  <section>
    <OptionCard description="Option card standalone preview">
      <template #selector>
        <OptionSelector label="Preview selector" :checked="true" />
      </template>
      <template #action>
        <button class="btn">Preview action</button>
      </template>
    </OptionCard>
  </section>
</template>

<script setup>
import OptionCard from '../../components/ui/OptionCard.vue'
import OptionSelector from '../../components/ui/OptionSelector.vue'
</script>

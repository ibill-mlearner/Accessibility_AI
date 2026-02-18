import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ComposerBar from '../../src/components/chat/ComposerBar.vue'

describe('ComposerBar.vue (AI input)', () => {
  it('emits send and model update for valid user input', async () => {
    const wrapper = mount(ComposerBar, {
      props: { showLogin: true, showModelSelect: true }
    })

    await wrapper.find('button.icon-btn').trigger('click')
    await wrapper.find('input').setValue('Summarize chapter 2')
    await wrapper.find('select').setValue('General')

    expect(wrapper.emitted('send')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['Summarize chapter 2'])
    expect(wrapper.emitted('update:selectedModel')[0]).toEqual(['General'])
  })

  it('does not render login/model controls when disabled', () => {
    const wrapper = mount(ComposerBar, {
      props: { showLogin: false, showModelSelect: false }
    })

    expect(wrapper.find('button.btn').exists()).toBe(false)
    expect(wrapper.find('select').exists()).toBe(false)
  })
})

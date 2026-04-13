import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ComposerBar from '../../src/components/chat/ComposerBar.vue'

describe('ComposerBar.vue (AI input)', () => {
  it('emits selected-model update when dropdown changes', async () => {
    const wrapper = mount(ComposerBar, {
      props: {
        showLogin: true,
        showModelSelect: true,
        selectedModel: 'huggingface::A',
        modelOptions: [
          { value: 'huggingface::A', label: 'Model A (huggingface)' },
          { value: 'huggingface::B', label: 'Model B (huggingface)' },
        ],
      }
    })

    await wrapper.find('select').setValue('huggingface::B')

    expect(wrapper.emitted('update:selected-model')).toEqual([['huggingface::B']])
  })

  it('does not render login button or model select when hidden', () => {
    const wrapper = mount(ComposerBar, {
      props: { showLogin: false, showModelSelect: false }
    })

    expect(wrapper.find('button.btn-outline-secondary').exists()).toBe(false)
    expect(wrapper.find('select').exists()).toBe(false)
  })
})

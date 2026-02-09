import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ComposerBar from '../../src/components/chat/ComposerBar.vue'

describe('ComposerBar.vue', () => {
  it('emits login and model updates', async () => {
    const wrapper = mount(ComposerBar, {
      props: { showLogin: true, showModelSelect: true }
    })

    await wrapper.find('button.btn').trigger('click')
    expect(wrapper.emitted('login')).toBeTruthy()

    await wrapper.find('select').setValue('General')
    expect(wrapper.emitted('update:selectedModel')[0]).toEqual(['General'])
  })
})

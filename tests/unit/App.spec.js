import { shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const bootstrap = vi.fn()

vi.mock('../../src/stores/appStore', () => ({
  useAppStore: () => ({
    error: 'mock error',
    bootstrap
  })
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/' })
}))

import App from '../../src/App.vue'

describe('App.vue', () => {
  it('calls bootstrap on mount and renders error message', () => {
    const wrapper = shallowMount(App, {
      global: {
        stubs: {
          SidebarNav: true,
          HeaderBar: true,
          RouterView: true
        }
      }
    })

    expect(bootstrap).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('mock error')
  })
})

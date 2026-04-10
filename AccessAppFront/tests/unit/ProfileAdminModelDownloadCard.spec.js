import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn()
}))

vi.mock('../../src/services/api', () => ({
  default: {
    post: postMock
  }
}))

import ProfileAdminModelDownloadCard from '../../src/components/profile/ProfileAdminModelDownloadCard.vue'

describe('ProfileAdminModelDownloadCard.vue', () => {
  afterEach(() => {
    postMock.mockReset()
  })

  it('starts a download request and cancels it', async () => {
    let capturedSignal = null
    postMock.mockImplementation((_url, _payload, config) => {
      capturedSignal = config?.signal || null
      return new Promise(() => {})
    })

    const wrapper = mount(ProfileAdminModelDownloadCard)

    await wrapper.find('#admin-model-id-input').setValue('Qwen/Qwen2.5-0.5B-Instruct')
    await wrapper.find('form').trigger('submit.prevent')

    expect(postMock).toHaveBeenCalledTimes(1)
    expect(capturedSignal).toBeTruthy()
    expect(capturedSignal.aborted).toBe(false)

    await wrapper.find('button.btn-outline-secondary').trigger('click')

    expect(capturedSignal.aborted).toBe(true)
  })
})

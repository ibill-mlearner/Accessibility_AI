import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}))

vi.mock('../../src/services/api', () => ({
  default: {
    post: postMock,
  },
}))

import { useChatStore } from '../../src/stores/chatStore'

describe('chatStore model selection API workflow', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    postMock.mockReset()
  })

  it('sends only provider + model_id to /api/v1/ai/selection and persists returned selection', async () => {
    const store = useChatStore()

    postMock.mockResolvedValueOnce({
      data: {
        provider: 'huggingface',
        id: 'Qwen/Qwen2.5-0.5B-Instruct',
        source: 'request_override',
      },
    })

    await store.updateModelSelection('huggingface::Qwen/Qwen2.5-0.5B-Instruct')

    expect(postMock).toHaveBeenCalledTimes(1)
    expect(postMock).toHaveBeenCalledWith('/api/v1/ai/selection', {
      provider: 'huggingface',
      model_id: 'Qwen/Qwen2.5-0.5B-Instruct',
    })
    expect(store.selectedModel).toBe('huggingface::Qwen/Qwen2.5-0.5B-Instruct')
    expect(store.lastPersistedSelection).toBe('huggingface::Qwen/Qwen2.5-0.5B-Instruct')
  })
})

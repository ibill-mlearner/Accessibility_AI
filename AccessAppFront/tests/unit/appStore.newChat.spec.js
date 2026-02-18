import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from '../../src/stores/appStore'
import api from '../../src/services/api'

vi.mock('../../src/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

describe('appStore new chat flow', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('creates a new chat when no active chat exists', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 333, title: 'New chat' } })
    const store = useAppStore()

    const chat = await store.ensureActiveChat({ user_id: 7, title: 'New chat' })

    expect(chat).toEqual({ id: 333, title: 'New chat' })
    expect(store.selectedChatId).toBe(333)
    expect(store.chats).toEqual([{ id: 333, title: 'New chat' }])
  })

  it('throws and stores error state when new chat creation fails', async () => {
    api.post.mockRejectedValueOnce(new Error('network'))
    const store = useAppStore()

    await expect(store.ensureActiveChat({ user_id: 7, title: 'Broken chat' })).rejects.toThrow(
      'Unable to start chat.'
    )

    expect(store.actionStatus.ensureActiveChat.error).toBe('Unable to start chat.')
    expect(store.chats).toEqual([])
  })
})

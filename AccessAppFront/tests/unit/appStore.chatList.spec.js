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

describe('appStore chat list', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads chat list and sets selected chat for valid payload', async () => {
    api.get.mockResolvedValueOnce({ data: [{ id: 101, title: 'Chat A' }] })
    const store = useAppStore()

    await store.fetchChats()

    expect(store.chats).toEqual([{ id: 101, title: 'Chat A' }])
    expect(store.selectedChatId).toBe(101)
    expect(store.actionStatus.fetchChats.error).toBe('')
  })

  it('raises malformed payload error for invalid chat list response', async () => {
    api.get.mockResolvedValueOnce({ data: { items: [] } })
    const store = useAppStore()

    await expect(store.fetchChats()).rejects.toMatchObject({
      message: 'Chats response payload was malformed.',
      kind: 'resource',
      resource: 'chats'
    })

    expect(store.actionStatus.fetchChats.error).toBe('Chats response payload was malformed.')
  })
})

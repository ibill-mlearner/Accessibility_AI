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

describe('appStore actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('bootstrap loads chats/classes/notes/features and selects first chat', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 101, name: 'Chat A' }] })
      .mockResolvedValueOnce({ data: [{ id: 1, role: 'student', name: 'Biology 103' }] })
      .mockResolvedValueOnce({ data: [{ id: 501, text: 'Saved note' }] })
      .mockResolvedValueOnce({ data: [{ id: 801, name: 'VoiceOver' }] })

    const store = useAppStore()

    await store.bootstrap()

    expect(api.get).toHaveBeenNthCalledWith(1, '/api/v1/chats')
    expect(api.get).toHaveBeenNthCalledWith(2, '/api/v1/classes')
    expect(api.get).toHaveBeenNthCalledWith(3, '/api/v1/notes')
    expect(api.get).toHaveBeenNthCalledWith(4, '/api/v1/features')

    expect(store.chats).toEqual([{ id: 101, name: 'Chat A' }])
    expect(store.classes).toEqual([{ id: 1, role: 'student', name: 'Biology 103' }])
    expect(store.notes).toEqual([{ id: 501, text: 'Saved note' }])
    expect(store.features).toEqual([{ id: 801, name: 'VoiceOver' }])
    expect(store.selectedChatId).toBe(101)
    expect(store.error).toBe('')
    expect(store.loading).toBe(false)
  })

  it('bootstrap sets selectedChatId to null when chats are empty', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })

    const store = useAppStore()
    await store.bootstrap()

    expect(store.selectedChatId).toBeNull()
    expect(store.error).toBe('')
    expect(store.loading).toBe(false)
  })

  it('bootstrap sets user-facing error when any request fails', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 101, name: 'Chat A' }] })
      .mockRejectedValueOnce(new Error('classes request failed'))

    const store = useAppStore()

    await store.bootstrap()

    expect(store.error).toBe('Unable to load data from the backend service. Please try again.')
    expect(store.loading).toBe(false)
  })

  it('login, logout, and setRole update role and selectedClassId as expected', () => {
    const store = useAppStore()
    store.selectedClassId = 42

    store.login()
    expect(store.role).toBe('student')
    expect(store.selectedClassId).toBe(42)

    store.setRole('instructor')
    expect(store.role).toBe('instructor')
    expect(store.selectedClassId).toBeNull()

    store.selectedClassId = 99
    store.logout()
    expect(store.role).toBe('guest')
    expect(store.selectedClassId).toBeNull()
  })
})

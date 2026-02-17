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

  it('bootstrap loads chats/classes/notes/features and selects first chat from items envelope', async () => {
    api.get
      .mockResolvedValueOnce({ data: { items: [{ id: 101, name: 'Chat A' }] } })
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

  it('fetchChats fails when collection payload is malformed', async () => {
    api.get.mockResolvedValueOnce({ data: { wrong: [] } })
    const store = useAppStore()

    await expect(store.fetchChats()).rejects.toMatchObject({
      message: 'Chats response payload was malformed.',
      kind: 'resource',
      resource: 'chats'
    })

    expect(store.actionStatus.fetchChats.error).toBe('Chats response payload was malformed.')
  })

  it('bootstrap sets selectedChatId to null when chats are empty', async () => {
    api.get
      .mockResolvedValueOnce({ data: { items: [] } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })

    const store = useAppStore()
    await store.bootstrap()

    expect(store.selectedChatId).toBeNull()
    expect(store.error).toBe('')
    expect(store.loading).toBe(false)
  })

  it('fetchClasses sets actionable endpoint-unavailable error and preserves state', async () => {
    const store = useAppStore()
    store.classes = [{ id: 22, role: 'student', name: 'Existing class' }]

    api.get.mockRejectedValueOnce({ response: { status: 404 } })

    await expect(store.fetchClasses()).rejects.toMatchObject({
      kind: 'unavailable',
      resource: 'classes',
      status: 404
    })

    expect(store.classes).toEqual([{ id: 22, role: 'student', name: 'Existing class' }])
    expect(store.actionStatus.fetchClasses.error).toBe(
      'Classes endpoint is unavailable. Enable /api/v1/classes or disable class-dependent UI.'
    )
  })

  it('bootstrap distinguishes auth errors from resource errors', async () => {
    api.get
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockRejectedValueOnce({ response: { status: 503 } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })

    const store = useAppStore()

    await store.bootstrap()

    expect(store.authError).toBe('Your session is invalid or expired. Please sign in again.')
    expect(store.error).toBe('Some application resources could not be loaded from the backend service.')
    expect(store.loading).toBe(false)
  })

  it('login, logout, and setRole update auth state and selectedClassId as expected', async () => {
    const store = useAppStore()
    store.selectedClassId = 42

    api.post.mockResolvedValueOnce({ data: { user: { id: 5, email: 'student@example.com', role: 'student' } } })

    await store.login({ email: 'student@example.com', password: 'secret' })
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      email: 'student@example.com',
      password: 'secret'
    })
    expect(store.role).toBe('student')
    expect(store.user).toEqual({ id: 5, email: 'student@example.com' })
    expect(store.authError).toBe('')
    expect(store.selectedClassId).toBe(42)

    store.setRole('instructor')
    expect(store.role).toBe('instructor')
    expect(store.selectedClassId).toBeNull()

    store.selectedClassId = 99
    store.logout()
    expect(store.role).toBe('guest')
    expect(store.user).toBeNull()
    expect(store.authError).toBe('')
    expect(store.selectedClassId).toBeNull()
  })

  it('login sets auth-specific error on 401/400 failures', async () => {
    const store = useAppStore()
    api.post.mockRejectedValueOnce({ response: { status: 401 } })

    await expect(store.login({ email: 'bad@example.com', password: 'wrong' })).rejects.toEqual({
      response: { status: 401 }
    })

    expect(store.authError).toBe('Invalid email or password.')
    expect(store.role).toBe('guest')
  })
})

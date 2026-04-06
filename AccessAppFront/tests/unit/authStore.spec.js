import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../../src/stores/authStore'
import { useChatStore } from '../../src/stores/chatStore'
import { useClassStore } from '../../src/stores/classStore'
import { useFeatureStore } from '../../src/stores/featureStore'
import api from '../../src/services/api'

vi.mock('../../src/services/api', () => ({
  default: {
    post: vi.fn()
  }
}))

describe('authStore clearAuthState', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    document.documentElement.style.fontSize = '22px'
    document.documentElement.style.fontFamily = 'Arial'
  })

  it('clears user-scoped stores and accessibility UI styles on logout', async () => {
    const auth = useAuthStore()
    const chats = useChatStore()
    const classes = useClassStore()
    const features = useFeatureStore()

    chats.selectedChatId = 101
    chats.chats = [{ id: 101, title: 'History' }]
    classes.selectedClassId = 44
    classes.classes = [{ id: 44, name: 'Physics' }]
    features.features = [{ id: 7, name: 'Large text', enabled: true, font_size_px: 24 }]
    features.selectedAccessibilityLinkIds = [7]

    api.post.mockResolvedValueOnce({ data: {} })
    await auth.logout()

    expect(auth.isAuthenticated).toBe(false)
    expect(chats.chats).toEqual([])
    expect(chats.selectedChatId).toBeNull()
    expect(classes.classes).toEqual([])
    expect(classes.selectedClassId).toBeNull()
    expect(features.features).toEqual([])
    expect(features.selectedAccessibilityLinkIds).toEqual([])
    expect(document.documentElement.style.fontSize).toBe('')
    expect(document.documentElement.style.fontFamily).toBe('')
  })
})

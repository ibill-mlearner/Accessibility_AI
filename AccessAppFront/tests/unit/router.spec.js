import { describe, expect, it } from 'vitest'
import router from '../../src/router'

describe('router', () => {
  it('defines core UX routes', () => {
    const paths = router.getRoutes().map((route) => route.path)

    expect(paths).toContain('/')
    expect(paths).toContain('/login')
    expect(paths).toContain('/logout')
    expect(paths).toContain('/classes/:role')
    expect(paths).toContain('/accessibility')
    expect(paths).toContain('/saved-notes')
  })

  it('redirects unknown routes to /error', async () => {
    await router.push('/this-route-does-not-exist')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/error')
  })
})

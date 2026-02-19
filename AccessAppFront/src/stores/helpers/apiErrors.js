export function isEndpointUnavailableStatus(status) {
  return [404, 405, 409, 501, 502, 503].includes(status)
}

export function toResourceError(error, 
    { 
        resourceLabel, 
        unavailableMessage, 
        fallbackMessage 
    }) {
  const status = error?.response?.status

  if (status === 401 || status === 403) {
    const e = new Error(`${resourceLabel} requires authentication.`)
    e.kind = 'auth'
    e.status = status
    e.resource = resourceLabel
    return e
  }

  if (isEndpointUnavailableStatus(status)) {
    const e = new Error(unavailableMessage)
    e.kind = 'unavailable'
    e.status = status
    e.resource = resourceLabel
    return e
  }

  const e = new Error(fallbackMessage)
  e.kind = 'resource'
  e.status = status
  e.resource = resourceLabel
  return e
}
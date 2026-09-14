async function req(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let msg = `请求失败（${res.status}）`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') msg = body.detail
    } catch {
      /* 保留默认提示 */
    }
    throw new Error(msg)
  }
  return res.status === 204 ? null : res.json()
}

const post = (path, data) =>
  req(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) })
const patch = (path, data) => req(path, { method: 'PATCH', body: JSON.stringify(data) })
const put = (path, data) => req(path, { method: 'PUT', body: JSON.stringify(data) })
const del = (path) => req(path, { method: 'DELETE' })

export const api = {
  // 窑炉档案
  listKilns: () => req('/kilns'),
  createKiln: (data) => post('/kilns', data),
  patchKiln: (id, data) => patch(`/kilns/${id}`, data),
  deleteKiln: (id, reassignTo) =>
    del(`/kilns/${id}${reassignTo ? `?reassign_to=${reassignTo}` : ''}`),
  // 窑次
  listFirings: () => req('/firings'),
  createFiring: (data) => post('/firings', data),
  getFiring: (id) => req(`/firings/${id}`),
  patchFiring: (id, data) => patch(`/firings/${id}`, data),
  deleteFiring: (id) => del(`/firings/${id}`),
  startFiring: (id) => post(`/firings/${id}/start`),
  openFiring: (id) => post(`/firings/${id}/open`),
  putCurve: (id, segments) => put(`/firings/${id}/curve`, { segments }),
  // 坯件
  addPiece: (firingId, name) => post(`/firings/${firingId}/pieces`, { name }),
  patchPiece: (id, data) => patch(`/pieces/${id}`, data),
  deletePiece: (id) => del(`/pieces/${id}`),
  placePiece: (id, shelf_layer, slot) => post(`/pieces/${id}/place`, { shelf_layer, slot }),
  unplacePiece: (id) => post(`/pieces/${id}/unplace`),
  // 看火
  addReading: (firingId, data) => post(`/firings/${firingId}/readings`, data),
  deleteReading: (id) => del(`/readings/${id}`),
  // 统计
  crackStats: () => req('/stats/cracks?limit=10'),
  crackStatsByKiln: () => req('/stats/cracks/by-kiln'),
}

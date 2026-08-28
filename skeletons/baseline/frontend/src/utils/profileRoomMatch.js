/**
 * 与 TicketStore.profileRoomMatches 同规则：building↔档案列、room⊆档案列。
 * matchProfileRoom 用（查寝默认楼栋/房间；实习绑岗可配单位/岗位）；勿在业务页另写一套比对。
 */

export function normRoomToken(s) {
  return String(s ?? '')
    .trim()
    .replace(/\s+/g, '')
    .toLowerCase()
}

export function profileRoomMatches(building, room, author, title, looseBuilding = false) {
  const b = normRoomToken(building)
  const r = normRoomToken(room)
  const a = normRoomToken(author)
  const t = normRoomToken(title)
  if (!b || !r) return false
  const buildingOk = looseBuilding
    ? b === a || a.includes(b) || b.includes(a)
    : b === a
  if (!buildingOk) return false
  return t === r || t.includes(r) || r.includes(t)
}

/** 资料楼栋/房间：宿舍 dorm* 或物业 house*（同一套比对，勿再分叉）。 */
export function profileSiteRoomFromExtras(extras = {}) {
  const building = String(extras.dormBuilding || extras.houseBuilding || '').trim()
  const room = String(extras.dormRoom || extras.houseNo || '').trim()
  return { building, room }
}

/** 报修 lookup：按资料楼栋松匹配楼栋行。 */
export function matchSiteByBuilding(sites, building, loose = true) {
  const b = normRoomToken(building)
  if (!b) return null
  return (
    (sites || []).find((s) => {
      const a = normRoomToken(s?.name)
      if (!a) return false
      return loose ? b === a || a.includes(b) || b.includes(a) : b === a
    }) || null
  )
}

/** 报修 lookup：楼栋已定后，按资料房间匹配房间/单元（code 或 name）。 */
export function matchUnitByRoom(units, building, room, siteName, looseBuilding = true) {
  return (
    (units || []).find((u) =>
      profileRoomMatches(building, room, siteName, u?.code || u?.name, looseBuilding),
    ) || null
  )
}

/** @param {object} [opts] buildingKey/roomKey/buildingField/roomField/looseBuilding */
export function filterArchiveByProfileRoom(items, extras = {}, opts = {}) {
  const buildingKey = opts.buildingKey || 'dormBuilding'
  const roomKey = opts.roomKey || 'dormRoom'
  const buildingField = opts.buildingField || 'author'
  const roomField = opts.roomField || 'title'
  const looseBuilding = !!opts.looseBuilding
  const building = extras[buildingKey] || ''
  const room = extras[roomKey] || ''
  if (!normRoomToken(building) || !normRoomToken(room)) return []
  return (items || []).filter((it) =>
    profileRoomMatches(
      building,
      room,
      it?.[buildingField],
      it?.[roomField],
      looseBuilding,
    ),
  )
}

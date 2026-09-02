/** @typedef {'locked'|'ready'|'generating'|'done'|'dirty'} PptPhase */

/** @typedef {'cover'|'toc'|'section'|'bullets'|'two-column'|'table'|'modules'|'er'|'demo'|'summary'} PageRole */

/**
 * @typedef {object} PptCover
 * @property {string} school
 * @property {string} college
 * @property {string} class_name
 * @property {string} student_name
 * @property {string} student_id
 * @property {string} advisor
 * @property {string|null} badge_data_url
 */

/**
 * @typedef {object} PptEvidence
 * @property {boolean} proposal
 * @property {boolean} modules
 * @property {boolean} er
 * @property {boolean} testcases
 * @property {boolean} gates_overall
 */

/**
 * @typedef {object} PptBullet
 * @property {string} id
 * @property {string} text
 * @property {boolean} [locked]
 * @property {string[]} [source_refs]
 */

/**
 * @typedef {object} PptPage
 * @property {string} id
 * @property {string} title
 * @property {PageRole} role
 * @property {PptBullet[]} [bullets]
 * @property {object} [cover]
 * @property {object} [figure]
 * @property {object} [table]
 * @property {string[]} [toc_items]
 */

/**
 * @typedef {object} PptDeck
 * @property {string} version
 * @property {string} theme
 * @property {string} layout_family
 * @property {string} master
 * @property {PptCover} cover
 * @property {PptPage[]} pages
 * @property {boolean} biz_dirty
 * @property {string} [title]
 */

/**
 * @typedef {object} PptUnit
 * @property {string} key
 * @property {string} title
 * @property {string} status
 * @property {string} [meta]
 */

/**
 * @typedef {object} PptJob
 * @property {number|string} id
 * @property {number} progress
 * @property {string} status
 * @property {{key:string,title:string,status:string,meta?:string}[]} [steps]
 * @property {PptUnit[]} [units]
 * @property {string} [error]
 */

/**
 * @typedef {object} PptCheckItem
 * @property {'error'|'warning'|'ok'} level
 * @property {string} code
 * @property {string} message
 */

/**
 * @typedef {object} PptStatus
 * @property {PptPhase} phase
 * @property {PptEvidence} evidence
 * @property {PptCover} cover
 * @property {string} theme
 * @property {string} layout_family
 * @property {string} master
 * @property {boolean} biz_dirty
 * @property {boolean} has_deck
 * @property {number} [page_count]
 * @property {PptJob|null} [job]
 * @property {string} [title]
 * @property {string} [deck_summary]
 */

export const PPT_PAGE_ROLES = [
  'cover',
  'toc',
  'section',
  'bullets',
  'two-column',
  'table',
  'modules',
  'er',
  'demo',
  'summary',
]

export const PPT_DIRTY_BANNER =
  '工程已更新，答辩 PPT 业务内容可能与实包不一致。主题/版式可保留；请先「按工程更新业务页」再导出。'

export const EMPTY_COVER = () => ({
  school: '',
  college: '',
  class_name: '',
  student_name: '',
  student_id: '',
  advisor: '',
  badge_data_url: null,
})

export function coverFieldsComplete(cover) {
  if (!cover) return false
  const texts = [
    cover.school,
    cover.college,
    cover.class_name,
    cover.student_name,
    cover.student_id,
    cover.advisor,
  ]
  return texts.every((t) => String(t || '').trim()) && !!cover.badge_data_url
}

export function emptyEvidence() {
  return {
    proposal: false,
    modules: false,
    er: false,
    testcases: false,
    gates_overall: false,
  }
}

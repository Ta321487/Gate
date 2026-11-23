import { highlightCode } from '../src/codeHighlight.js'

const sql = [
  '-- 订单表',
  'CREATE TABLE IF NOT EXISTS `t_4_6` (',
  "  `id` bigint NOT NULL COMMENT '主键',",
  '  PRIMARY KEY (`id`)',
  ') ENGINE=InnoDB;',
].join('\n')

const h = highlightCode(sql, 'sql')
if (!h.includes('tok-kw') || !h.includes('tok-cmt') || !h.includes('tok-str')) {
  throw new Error(`sql tokens missing: ${h.slice(0, 240)}`)
}

const j = highlightCode(JSON.stringify({ a: 1, b: 'x', c: null }, null, 2), 'json')
if (!j.includes('tok-key') || !j.includes('tok-num') || !j.includes('tok-kw')) {
  throw new Error(`json tokens missing: ${j.slice(0, 240)}`)
}

const evil = highlightCode('<img onerror=alert(1)>', 'plain')
if (evil.includes('<img') || !evil.includes('&lt;img')) {
  throw new Error('escape fail')
}

console.log('highlight ok')

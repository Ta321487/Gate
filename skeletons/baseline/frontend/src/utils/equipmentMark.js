/**
 * 会议室设备名 → 演示用单字图标（非独立图标库）。
 * 按关键词命中；未命中用「设」。
 */
const RULES = [
  [/投影|幕布|PPT|投屏/i, '投'],
  [/电视|显示|屏|监视/i, '屏'],
  [/音响|音箱|麦克|话筒|音频|扩音/i, '音'],
  [/电脑|主机|笔记本|PC/i, '脑'],
  [/摄像|相机|录像/i, '摄'],
  [/白板|黑板|书写/i, '板'],
  [/空调|新风|温控/i, '风'],
  [/桌|椅|沙发|家具/i, '桌'],
  [/灯|照明/i, '灯'],
  [/网|路由|交换机|Wi-?Fi/i, '网'],
  [/打印|复印|扫描/i, '印'],
  [/实验|仪器|显微镜/i, '仪'],
  [/床|被褥|床位/i, '床'],
]

export function equipmentMark(name) {
  const s = String(name || '').trim()
  if (!s) return '设'
  for (const [re, mark] of RULES) {
    if (re.test(s)) return mark
  }
  return s.slice(0, 1)
}

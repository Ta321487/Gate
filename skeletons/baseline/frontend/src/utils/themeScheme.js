/** 行业配色是否为深色壳（与 themes.css 深色选择器保持一致） */
export function isDarkTheme(themeId) {
  const id = String(themeId || '')
  if (!id) return false
  if (id.endsWith('-night') || id === 'theme-night') return true
  return id === 'media-cinema' || id === 'music-vinyl'
}

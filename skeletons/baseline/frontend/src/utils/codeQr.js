/** 码字符串 → DataURL（E-07）；依赖 qrcode。 */
import QRCode from 'qrcode'

export async function codeToDataUrl(text, opts = {}) {
  const raw = text == null ? '' : String(text).trim()
  if (!raw) return ''
  return QRCode.toDataURL(raw, {
    errorCorrectionLevel: 'M',
    margin: 2,
    width: opts.width || 220,
    color: { dark: '#111827', light: '#ffffff' },
  })
}

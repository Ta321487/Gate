/** 近白像素变透明（校徽可选去白底；徽+字可能扣不干净） */
export function knockNearWhiteToAlpha(sourceUrl) {
  return new Promise((resolve) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = image.naturalWidth || image.width
      canvas.height = image.naturalHeight || image.height
      const ctx = canvas.getContext('2d')
      if (!ctx || !canvas.width) {
        resolve({ url: sourceUrl, changed: false })
        return
      }
      ctx.drawImage(image, 0, 0)
      const frame = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const d = frame.data
      let changed = 0
      for (let i = 0; i < d.length; i += 4) {
        if (d[i] > 245 && d[i + 1] > 245 && d[i + 2] > 245 && d[i + 3] > 0) {
          d[i + 3] = 0
          changed++
        }
      }
      if (changed) ctx.putImageData(frame, 0, 0)
      resolve({ url: canvas.toDataURL('image/png'), changed: changed > 0 })
    }
    image.onerror = () => resolve({ url: sourceUrl, changed: false })
    image.src = sourceUrl
  })
}

export function readBlobAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error || new Error('read failed'))
    reader.readAsDataURL(blob)
  })
}

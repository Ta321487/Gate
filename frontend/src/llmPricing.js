/**
 * 大模型相对单价（元 / 百万 tokens），仅用于预算接近时比贵锁厂商，非财务结算。
 * 后续接新模型：在 MODEL_PRICES 加一行即可。
 *
 * DeepSeek：官方人民币，缓存未命中 + 非高峰。
 * Gemini：官方美元 × USD_TO_CNY。
 */

/** 美元兑人民币；汇率变了只改这里。 */
export const USD_TO_CNY = 7.2

/** 输入/输出混合权重（工厂调用偏输入） */
export const INPUT_WEIGHT = 0.7
export const OUTPUT_WEIGHT = 0.3

/**
 * @typedef {{ currency: 'CNY' | 'USD', inputPer1M: number, outputPer1M: number }} ModelPrice
 * @type {Record<string, ModelPrice>}
 */
export const MODEL_PRICES = {
  'deepseek-v4-flash': { currency: 'CNY', inputPer1M: 1, outputPer1M: 2 },
  'deepseek-v4-pro': { currency: 'CNY', inputPer1M: 3, outputPer1M: 6 },
  'gemini-2.5-flash': { currency: 'USD', inputPer1M: 0.3, outputPer1M: 2.5 },
  'gemini-2.5-pro': { currency: 'USD', inputPer1M: 1.25, outputPer1M: 10 },
  'gemini-2.0-flash': { currency: 'USD', inputPer1M: 0.1, outputPer1M: 0.4 },
}

/**
 * @param {string | null | undefined} modelId
 * @returns {number | null} 混合单价（元 / 1M tokens）；未知模型返回 null
 */
export function blendYuanPer1M(modelId) {
  if (!modelId) return null
  const row = MODEL_PRICES[modelId]
  if (!row) return null
  const fx = row.currency === 'USD' ? USD_TO_CNY : 1
  const input = row.inputPer1M * fx
  const output = row.outputPer1M * fx
  return INPUT_WEIGHT * input + OUTPUT_WEIGHT * output
}

/**
 * 双开时返回更贵的一方；同价（差 < 1%）或无法比价时返回 null。
 * @param {{ deepseekModel?: string, geminiModel?: string }} opts
 * @returns {'deepseek' | 'gemini' | null}
 */
export function pricierProvider({ deepseekModel, geminiModel } = {}) {
  const ds = blendYuanPer1M(deepseekModel)
  const gm = blendYuanPer1M(geminiModel)
  if (ds == null || gm == null) return null
  const hi = Math.max(ds, gm)
  if (hi <= 0) return null
  if (Math.abs(ds - gm) / hi < 0.01) return null
  return gm > ds ? 'gemini' : 'deepseek'
}

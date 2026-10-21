<template>
  <router-link
    v-if="show"
    to="/cart"
    class="cart-badge-link"
    title="购物车"
  >
    <el-badge :value="count || undefined" :hidden="!count" :max="99">
      <el-icon :size="18" class="cart-ico"><ShoppingCart /></el-icon>
    </el-badge>
  </router-link>
</template>

<script setup>
/** 门户顶栏购物车角标：矢量图标 + 数量；与文字主路径不同时出，避免叠两份 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ShoppingCart } from '@element-plus/icons-vue'
import http from '../api/http'
import { hasCap, schemaMenus } from '../utils/domainSchema.js'
import { isLoggedIn } from '../utils/session.js'

const route = useRoute()
const count = ref(0)

const show = computed(() => {
  if (!hasCap('order_lines') || !isLoggedIn()) return false
  return schemaMenus('user').some((m) => m.key === 'cart')
})

async function refresh() {
  if (!show.value) {
    count.value = 0
    return
  }
  try {
    const res = await http.get('/api/cart')
    const raw = res.data?.list ?? res.data
    const rows = Array.isArray(raw) ? raw : []
    count.value = rows.reduce((n, x) => n + (Number(x.qty) || 1), 0)
  } catch {
    count.value = 0
  }
}

let timer = null
onMounted(() => {
  refresh()
  timer = setInterval(refresh, 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
watch(() => route.fullPath, refresh)
</script>

<style scoped>
.cart-badge-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  margin-right: 2px;
  padding: 4px 6px;
  border-radius: 8px;
  color: var(--portal-muted, #5b6b76);
}
.cart-badge-link:hover {
  color: var(--portal-ink, #15202b);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
}
.cart-ico { display: block; line-height: 1; }
</style>

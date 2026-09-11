<template>
  <router-link
    v-if="show"
    to="/cart"
    class="cart-badge-link"
    title="购物车"
  >
    <el-badge :value="count || undefined" :hidden="!count" :max="99">
      <span class="cart-ico" aria-hidden="true">🛒</span>
    </el-badge>
  </router-link>
</template>

<script setup>
/** 门户顶栏购物车角标：有 order_lines 且用户菜单含 cart 时显示 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
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
  color: inherit;
}
.cart-ico { font-size: 15px; line-height: 1; }
</style>

<template>
  <aside v-if="items.length" class="side-rail" aria-label="快捷入口">
    <div class="rail-stack">
      <router-link
        v-for="item in outside"
        :key="item.key"
        :to="item.to"
        class="rail-btn"
        :class="{ 'is-active': navItemActive(route.path, item.to) }"
        :title="item.label"
      >
        <el-icon :size="18"><component :is="iconOf(item.key)" /></el-icon>
        <span class="rail-cap">{{ shortLabel(item.label) }}</span>
      </router-link>

      <el-popover
        v-if="more.length"
        placement="left-start"
        :width="200"
        trigger="hover"
        :show-after="120"
        teleported
        popper-class="portal-side-rail-more"
      >
        <template #reference>
          <button type="button" class="rail-btn rail-more-trig" title="更多入口">
            <el-icon :size="18"><MoreFilled /></el-icon>
            <span class="rail-cap">更多</span>
          </button>
        </template>
        <div class="more-list">
          <router-link
            v-for="item in more"
            :key="item.key"
            :to="item.to"
            class="more-row"
            :class="{ 'is-active': navItemActive(route.path, item.to) }"
            @click="pinOutside(item.key)"
          >
            <el-icon :size="16"><component :is="iconOf(item.key)" /></el-icon>
            <span>{{ item.label }}</span>
            <span class="pin-hint">钉住</span>
          </router-link>
        </div>
      </el-popover>

      <button type="button" class="rail-btn rail-edit" title="编辑入口" @click="editOpen = true">
        <el-icon :size="18"><Setting /></el-icon>
        <span class="rail-cap">编辑</span>
      </button>
    </div>
  </aside>

  <!-- 必须挂到 body：侧栏有定位上下文时，弹层留在 aside 内会被压成一条缝，遮罩却仍盖全屏导致整页点不了 -->
  <el-dialog
    v-model="editOpen"
    title="快捷入口"
    width="420px"
    align-center
    teleported
    append-to-body
    destroy-on-close
    class="portal-side-rail-edit"
  >
    <p class="edit-lead">勾选外侧显示（最多 {{ RAIL_OUTSIDE_MAX }} 个），可上下调整顺序。只改本机。</p>
    <ul class="edit-list">
      <li v-for="(row, idx) in editRows" :key="row.key" class="edit-row">
        <div class="edit-moves">
          <button type="button" class="edit-handle" title="上移" @click="moveEdit(idx, -1)">↑</button>
          <button type="button" class="edit-handle" title="下移" @click="moveEdit(idx, 1)">↓</button>
        </div>
        <el-checkbox v-model="row.outside" :disabled="outsideDisabled(row)">
          {{ row.label }}
        </el-checkbox>
      </li>
    </ul>
    <template #footer>
      <el-button @click="editOpen = false">取消</el-button>
      <el-button type="primary" @click="saveEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  ChatLineSquare,
  Clock,
  CollectionTag,
  Location,
  Money,
  MoreFilled,
  Notebook,
  Setting,
  ShoppingBag,
  Star,
  Ticket,
  Wallet,
} from '@element-plus/icons-vue'
import { navItemActive } from '../utils/navOverflow.js'
import {
  RAIL_OUTSIDE_MAX,
  arrangeSideRail,
  loadRailPreference,
  saveRailPreference,
} from '../utils/portalShellNav.js'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const route = useRoute()
const pref = ref(loadRailPreference())
const editOpen = ref(false)
const editRows = ref([])

const arranged = computed(() => arrangeSideRail(props.items, pref.value))
const outside = computed(() => arranged.value.outside)
const more = computed(() => arranged.value.more)

const ICON_MAP = {
  favorites: Star,
  dm: ChatDotRound,
  browse_history: Clock,
  order_reviews: ChatLineSquare,
  addresses: Location,
  guestbook: Notebook,
  coupons: Ticket,
  points_ledger: Money,
  points_rules: CollectionTag,
  blind_draws: ShoppingBag,
  my_consigns: ShoppingBag,
  my_buybacks: ShoppingBag,
  my_digital: Ticket,
  balance_mine: Wallet,
  balance_ledger_mine: Wallet,
}

function iconOf(key) {
  return ICON_MAP[key] || CollectionTag
}

function shortLabel(label) {
  const s = String(label || '')
  return s.length <= 2 ? s : s.slice(0, 2)
}

function pinOutside(key) {
  const cur = arrangeSideRail(props.items, pref.value)
  let outsideKeys = [...cur.outsideKeys]
  if (outsideKeys.includes(key)) return
  if (outsideKeys.length >= RAIL_OUTSIDE_MAX) {
    outsideKeys = [...outsideKeys.slice(1), key]
  } else {
    outsideKeys.push(key)
  }
  const next = { order: cur.order, outside: outsideKeys }
  saveRailPreference(next)
  pref.value = next
}

function outsideDisabled(row) {
  if (row.outside) return false
  const n = editRows.value.filter((r) => r.outside).length
  return n >= RAIL_OUTSIDE_MAX
}

function moveEdit(idx, delta) {
  const next = idx + delta
  if (next < 0 || next >= editRows.value.length) return
  const copy = [...editRows.value]
  const [row] = copy.splice(idx, 1)
  copy.splice(next, 0, row)
  editRows.value = copy
}

watch(editOpen, (open) => {
  if (!open) return
  const cur = arrangeSideRail(props.items, pref.value)
  const outsideSet = new Set(cur.outsideKeys)
  editRows.value = cur.order.map((key) => {
    const hit = props.items.find((x) => x.key === key)
    return {
      key,
      label: hit?.label || key,
      outside: outsideSet.has(key),
    }
  })
})

function saveEdit() {
  const order = editRows.value.map((r) => r.key)
  const outsideKeys = editRows.value.filter((r) => r.outside).map((r) => r.key).slice(0, RAIL_OUTSIDE_MAX)
  const next = { order, outside: outsideKeys }
  saveRailPreference(next)
  pref.value = next
  editOpen.value = false
}
</script>

<style scoped>
.side-rail {
  /* 不用 transform：会形成 containing block，子级 fixed/弹层被箍在窄条里 */
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  padding: 8px 0 8px 0;
  pointer-events: none;
  width: auto;
  max-width: 72px;
}
.rail-stack {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 6px;
  background: color-mix(in srgb, var(--portal-surface, #fff) 94%, transparent);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-right: none;
  border-radius: 10px 0 0 10px;
  box-shadow: -2px 4px 16px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}
.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 48px;
  padding: 8px 4px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--portal-muted, #5b6b76);
  text-decoration: none;
  cursor: pointer;
  font-size: 11px;
  line-height: 1.2;
}
.rail-btn:hover,
.rail-btn.is-active {
  color: var(--portal-ink, #15202b);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 14%, transparent);
}
.rail-cap {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rail-edit {
  margin-top: 4px;
  border-top: 1px solid var(--portal-line, #e2e8f0);
  border-radius: 0 0 8px 8px;
}
.more-list { display: flex; flex-direction: column; gap: 2px; }
.more-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--portal-ink, #15202b);
  text-decoration: none;
  font-size: 13px;
}
.more-row:hover,
.more-row.is-active {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
}
.pin-hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--portal-muted, #94a3b8);
}
</style>

<!-- 弹层挂 body 后 scoped 失效，用非 scoped 补样式 -->
<style>
.portal-side-rail-edit .edit-lead {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
  line-height: 1.5;
}
.portal-side-rail-edit .edit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 320px;
  overflow: auto;
}
.portal-side-rail-edit .edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--portal-line, #eef2f5);
}
.portal-side-rail-edit .edit-moves {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
.portal-side-rail-edit .edit-handle {
  width: 28px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: 4px;
  background: var(--portal-surface, #fff);
  color: var(--portal-muted, #94a3b8);
  cursor: pointer;
  line-height: 1;
  font-size: 12px;
}
.portal-side-rail-edit .edit-handle:hover {
  color: var(--portal-accent, #0b6e75);
  border-color: var(--portal-accent, #0b6e75);
}
.portal-side-rail-edit .el-checkbox {
  flex: 1;
  min-width: 0;
}
</style>

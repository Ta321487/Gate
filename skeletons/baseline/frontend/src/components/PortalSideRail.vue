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
        <span class="rail-mark">
          <el-icon :size="16"><component :is="iconOf(item.key)" /></el-icon>
        </span>
        <span class="rail-cap">{{ railShortLabel(item.label, item.key) }}</span>
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
            <span class="rail-mark rail-mark--more">
              <el-icon :size="16"><MoreFilled /></el-icon>
            </span>
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
            <span class="rail-mark rail-mark--sm">
              <el-icon :size="14"><component :is="iconOf(item.key)" /></el-icon>
            </span>
            <span>{{ item.label }}</span>
            <span class="pin-hint">钉住</span>
          </router-link>
        </div>
      </el-popover>

      <button type="button" class="rail-btn rail-edit" title="编辑入口" @click="editOpen = true">
        <span class="rail-mark">
          <el-icon :size="16"><Setting /></el-icon>
        </span>
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
      <li
        v-for="(row, idx) in editRows"
        :key="row.key"
        class="edit-row"
        :class="{ on: row.outside }"
      >
        <el-checkbox
          v-model="row.outside"
          :disabled="outsideDisabled(row)"
          class="edit-pick"
        >
          <span class="edit-pick-inner">
            <span class="rail-mark rail-mark--sm">
              <el-icon :size="14"><component :is="iconOf(row.key)" /></el-icon>
            </span>
            <span class="edit-name">{{ row.label }}</span>
          </span>
        </el-checkbox>
        <div class="edit-moves">
          <button
            type="button"
            class="edit-handle"
            title="上移"
            :disabled="idx === 0"
            @click="moveEdit(idx, -1)"
          >↑</button>
          <button
            type="button"
            class="edit-handle"
            title="下移"
            :disabled="idx === editRows.length - 1"
            @click="moveEdit(idx, 1)"
          >↓</button>
        </div>
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
  railShortLabel,
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
  return editRows.value.filter((r) => r.outside).length >= RAIL_OUTSIDE_MAX
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
  const outsideKeys = editRows.value
    .filter((r) => r.outside)
    .map((r) => r.key)
    .slice(0, RAIL_OUTSIDE_MAX)
  const next = { order, outside: outsideKeys }
  saveRailPreference(next)
  pref.value = next
  editOpen.value = false
}</script>

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
  padding: 8px 0;
  pointer-events: none;
  width: auto;
  max-width: 72px;
}
.rail-stack {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
  width: 56px;
  padding: 8px 6px;
  background: color-mix(in srgb, var(--portal-surface, #fff) 94%, transparent);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-right: none;
  border-radius: 10px 0 0 10px;
  box-shadow: -2px 4px 16px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
  box-sizing: border-box;
}
.rail-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  margin: 0;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--portal-muted, #5b6b76);
  text-decoration: none;
  cursor: pointer;
  font-size: 11px;
  line-height: 1.15;
  box-sizing: border-box;
}
.rail-mark {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--portal-accent, #0b6e75);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
}
.rail-mark--more {
  color: #fff;
  background: var(--portal-accent, #0b6e75);
}
.rail-mark--sm {
  width: 22px;
  height: 22px;
  border-radius: 6px;
}
.rail-mark :deep(.el-icon) {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
}
.rail-btn:hover,
.rail-btn.is-active {
  color: var(--portal-ink, #15202b);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, transparent);
}
.rail-btn:hover .rail-mark,
.rail-btn.is-active .rail-mark {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, transparent);
}
.rail-cap {
  display: block;
  width: 100%;
  text-align: center;
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 64px;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 8px;
  border-radius: 8px;
}
.portal-side-rail-edit .edit-row:hover {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 6%, transparent);
}
.portal-side-rail-edit .edit-row.on {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, transparent);
}
.portal-side-rail-edit .edit-pick {
  min-width: 0;
  height: auto;
  margin-right: 0;
}
.portal-side-rail-edit .edit-pick .el-checkbox__label {
  min-width: 0;
  padding-left: 10px;
  line-height: 1.3;
}
.portal-side-rail-edit .edit-pick-inner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  vertical-align: middle;
}
.portal-side-rail-edit .edit-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: var(--portal-ink, #15202b);
}
.portal-side-rail-edit .edit-moves {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.portal-side-rail-edit .edit-handle {
  width: 30px;
  height: 30px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--portal-muted, #94a3b8);
  cursor: pointer;
  line-height: 1;
  font-size: 14px;
}
.portal-side-rail-edit .edit-handle:hover:not(:disabled) {
  color: var(--portal-accent, #0b6e75);
  background: var(--portal-surface, #fff);
  box-shadow: 0 0 0 1px var(--portal-line, #e2e8f0);
}
.portal-side-rail-edit .edit-handle:disabled {
  opacity: 0.28;
  cursor: not-allowed;
}
.portal-side-rail-edit .rail-mark {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--portal-accent, #0b6e75);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
}
.portal-side-rail-edit .rail-mark--sm {
  width: 22px;
  height: 22px;
  border-radius: 6px;
}
.portal-side-rail-edit .rail-mark .el-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
}
</style>

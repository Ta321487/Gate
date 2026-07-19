<template>
  <div v-if="show" class="guest-hint">
    <button type="button" class="guest-cta" @click="onClick">{{ text }}</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  guestLoginCta,
  isGuestBrowseEnabled,
  isLoggedIn,
  requireLogin,
} from '../utils/session.js'

const props = defineProps({
  /** 覆盖工厂文案（一般不用） */
  label: { type: String, default: '' },
})

const router = useRouter()
const show = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const text = computed(() => (props.label || guestLoginCta()).trim() || '登录查看更多')

function onClick() {
  requireLogin(router)
}
</script>

<style scoped>
.guest-hint {
  margin-top: 20px;
  padding: 8px 0 4px;
  text-align: center;
}
.guest-cta {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-color-primary, #409eff);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.guest-cta:hover {
  opacity: 0.85;
}
</style>

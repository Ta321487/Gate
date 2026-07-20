<template>
  <section v-if="slides.length" class="stage" aria-roledescription="carousel" :aria-label="ariaLabel">
    <div class="stage-track">
      <article
        v-for="(s, i) in slides"
        :key="s.src + i"
        class="slide"
        :class="{ on: i === index }"
        :aria-hidden="i !== index"
      >
        <div class="photo" :style="{ backgroundImage: `url('${s.src}')` }" />
        <div class="veil" />
        <div class="copy">
          <p class="kicker">{{ brand }}</p>
          <h2>{{ s.title }}</h2>
          <p v-if="s.lead" class="lead">{{ s.lead }}</p>
        </div>
      </article>
    </div>
    <div class="dots" role="tablist">
      <button
        v-for="(s, i) in slides"
        :key="'d' + i"
        type="button"
        role="tab"
        :aria-selected="i === index"
        :class="{ on: i === index }"
        @click="go(i)"
      >
        <span class="sr">第 {{ i + 1 }} 帧</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { APP_DELIVERED } from '../appDelivered.js'
import { schemaLabels } from '../utils/domainSchema.js'

const props = defineProps({
  intervalMs: { type: Number, default: 5600 },
})

const raw = computed(() => {
  const list = APP_DELIVERED?.portalBanners
  return Array.isArray(list) ? list.filter((x) => x && x.src) : []
})
const slides = ref([])
const index = ref(0)
const labels = schemaLabels()
const brand = computed(() => labels.appName || APP_DELIVERED.title || '门户')
const ariaLabel = computed(() => `${brand.value}轮播`)

let timer = null

function go(i) {
  index.value = i
  restart()
}

function next() {
  if (slides.value.length < 2) return
  index.value = (index.value + 1) % slides.value.length
}

function restart() {
  if (timer) clearInterval(timer)
  if (slides.value.length > 1) {
    timer = setInterval(next, props.intervalMs)
  }
}

function isWelcomeSlide(s) {
  const t = String(s?.title || '').trim()
  return t === '欢迎使用' || t.startsWith('欢迎')
}

function orderSlides(list) {
  const welcome = []
  const rest = []
  for (const s of list) {
    if (isWelcomeSlide(s)) welcome.push(s)
    else rest.push(s)
  }
  return [...welcome, ...rest]
}

async function probe() {
  const ok = []
  for (const s of raw.value) {
    const pass = await new Promise((resolve) => {
      const img = new Image()
      img.onload = () => resolve(true)
      img.onerror = () => resolve(false)
      img.src = s.src
    })
    if (pass) ok.push(s)
  }
  slides.value = orderSlides(ok)
  index.value = 0
  restart()
}

watch(raw, () => probe(), { deep: true })

onMounted(probe)
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.stage {
  position: relative;
  height: clamp(200px, 32vw, 320px);
  overflow: hidden;
  background: #0f1720;
  isolation: isolate;
}
.stage-track { position: absolute; inset: 0; }
.slide {
  position: absolute; inset: 0;
  opacity: 0;
  transition: opacity 0.9s ease;
  pointer-events: none;
}
.slide.on { opacity: 1; pointer-events: auto; }
.photo {
  position: absolute; inset: -4%;
  background-size: cover;
  background-position: center;
  transform: scale(1.04);
  transition: transform 7s ease-out;
}
.slide.on .photo { transform: scale(1.12); }
.veil {
  position: absolute; inset: 0;
  background:
    linear-gradient(105deg, rgba(8, 14, 20, 0.78) 0%, rgba(8, 14, 20, 0.35) 48%, rgba(8, 14, 20, 0.15) 100%),
    linear-gradient(0deg, rgba(8, 14, 20, 0.45) 0%, transparent 45%);
}
.copy {
  position: relative;
  z-index: 1;
  height: 100%;
  max-width: 1080px;
  margin: 0 auto;
  padding: 36px 28px 48px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 6px;
  color: #f4f7f8;
  animation: rise 0.7s ease both;
  box-sizing: border-box;
}
.slide.on .copy { animation: rise 0.75s ease both; }
@keyframes rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: color-mix(in srgb, #fff 72%, var(--portal-accent, #5eead4));
  font-family: var(--portal-font-ui);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.copy h2 {
  margin: 0;
  font-family: var(--portal-font-display);
  font-size: clamp(24px, 3.8vw, 36px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  text-shadow: 0 2px 24px rgba(0, 0, 0, 0.35);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lead {
  margin: 0;
  max-width: 36em;
  font-size: 14px;
  line-height: 1.55;
  color: rgba(244, 247, 248, 0.88);
  font-family: var(--portal-font-ui);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dots {
  position: absolute;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  z-index: 2;
}
.dots button {
  width: 28px;
  height: 3px;
  padding: 0;
  border: 0;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.35);
  cursor: pointer;
  transition: background 0.25s, width 0.25s;
}
.dots button.on {
  width: 40px;
  background: #fff;
}
.sr {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); border: 0;
}
@media (max-width: 640px) {
  .copy { padding: 28px 18px 44px; }
  .lead { font-size: 13px; }
}
</style>

<template>
  <div class="ppt-slide" :class="slideClass">
    <div v-if="layoutFamily !== 'center'" class="ppt-slide-band" />
    <div class="ppt-slide-body">
      <template v-if="page?.role === 'cover'">
        <img
          v-if="cover.badge_data_url"
          class="ppt-slide-badge"
          :src="cover.badge_data_url"
          alt="校徽"
        />
        <div class="ppt-slide-school">{{ cover.school || '学校' }} · {{ cover.college || '学院' }}</div>
        <h2>{{ deckTitle }}</h2>
        <div class="ppt-slide-meta">
          {{ cover.class_name || '班级' }} · {{ cover.student_name || '姓名' }} · {{ cover.student_id || '学号' }}
          <br />
          指导教师：{{ cover.advisor || '导师' }}
        </div>
      </template>

      <template v-else-if="page?.role === 'toc'">
        <h2>{{ page.title }}</h2>
        <ol class="ppt-toc-list">
          <li v-for="(t, i) in page.toc_items || []" :key="i">{{ t }}</li>
        </ol>
      </template>

      <template v-else>
        <h2>{{ page?.title }}</h2>
        <div
          v-if="page?.figure"
          class="ppt-figure-slot"
          :class="{ 'is-missing': page.figure.missing }"
        >
          <span v-if="page.figure.missing">{{ page.figure.hint || page.figure.label || '缺图' }}</span>
          <span v-else>{{ page.figure.label || '图示' }}</span>
        </div>
        <table v-if="page?.table" class="ppt-mini-table">
          <thead>
            <tr>
              <th v-for="(h, i) in page.table.headers || []" :key="i">{{ h }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in page.table.rows || []" :key="ri">
              <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
        <ul v-if="page?.bullets?.length" class="ppt-bullets">
          <li
            v-for="b in page.bullets"
            :key="b.id"
            :class="{ 'is-locked': b.locked }"
          >
            <span
              class="ppt-bullet-text"
              contenteditable="true"
              @blur="onBulletBlur(b, $event)"
              @keydown.enter.prevent="$event.target.blur()"
            >{{ b.text }}</span>
            <span v-if="b.locked" class="pill pill-amber" style="margin-left:6px;font-size:10px">locked</span>
          </li>
        </ul>
        <div v-if="editable && page?.bullets?.length" class="row mt-8" style="gap:6px;flex-wrap:wrap">
          <n-button
            v-for="b in page.bullets"
            :key="'lock-' + b.id"
            size="tiny"
            quaternary
            @click="emit('toggle-lock', b.id)"
          >
            {{ b.locked ? '解锁' : '锁定' }} · {{ shortId(b.id) }}
          </n-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Object, default: null },
  cover: { type: Object, default: () => ({}) },
  deckTitle: { type: String, default: '毕业设计答辩' },
  layoutFamily: { type: String, default: 'band' },
  editable: { type: Boolean, default: true },
})
const emit = defineEmits(['save-bullet', 'toggle-lock'])

const slideClass = computed(() => {
  const role = props.page?.role
  const fam = props.layoutFamily
  return {
    'is-modules': role === 'modules',
    'is-er': role === 'er',
    'is-demo': role === 'demo',
    'is-center': fam === 'center',
    'is-footer': fam === 'footer',
  }
})

function shortId(id) {
  return String(id || '').split('-').pop() || id
}

function onBulletBlur(b, e) {
  if (!props.editable) return
  const text = String(e.target?.innerText || '').trim()
  if (text !== b.text) emit('save-bullet', b.id, text)
}
</script>

<template>
  <div class="motif" :data-motif="name" aria-hidden="true">
    <svg viewBox="0 0 120 120" class="motif-svg">
      <!-- book -->
      <g v-if="name === 'book'">
        <path class="fill-soft" d="M22 28h34c8 0 14 4 14 12v54c0-6-6-10-14-10H22V28z" />
        <path class="stroke" d="M56 28c8 0 14 4 14 12v54M22 28h34c8 0 14 4 14 12v54H22V28z" fill="none" />
        <path class="stroke" d="M70 28h28c6 0 10 4 10 10v56H70c-8 0-14 4-14 10V40c0-8 6-12 14-12z" fill="none" />
        <path class="accent" d="M78 48h22M78 60h18M78 72h20" />
      </g>
      <!-- gear -->
      <g v-else-if="name === 'gear'">
        <circle class="fill-soft" cx="60" cy="60" r="22" />
        <circle class="stroke" cx="60" cy="60" r="14" fill="none" />
        <circle class="accent-dot" cx="60" cy="60" r="5" />
        <g class="stroke" fill="none">
          <rect x="54" y="18" width="12" height="16" rx="2" />
          <rect x="54" y="86" width="12" height="16" rx="2" />
          <rect x="18" y="54" width="16" height="12" rx="2" />
          <rect x="86" y="54" width="16" height="12" rx="2" />
        </g>
      </g>
      <!-- box -->
      <g v-else-if="name === 'box'">
        <path class="fill-soft" d="M24 44l36-16 36 16v40L60 100 24 84V44z" />
        <path class="stroke" d="M24 44l36-16 36 16v40L60 100 24 84V44zM24 44l36 16 36-16M60 60v40" fill="none" />
      </g>
      <!-- cart -->
      <g v-else-if="name === 'cart'">
        <path class="stroke" d="M20 32h12l10 48h48l10-32H42" fill="none" />
        <circle class="accent-dot" cx="48" cy="92" r="6" />
        <circle class="accent-dot" cx="82" cy="92" r="6" />
        <path class="fill-soft" d="M44 48h46l-6 20H50z" />
      </g>
      <!-- bed -->
      <g v-else-if="name === 'bed'">
        <path class="fill-soft" d="M18 58h84v28H18z" />
        <path class="stroke" d="M18 86V48h24v10h60v28H18zM18 66h84" fill="none" />
        <circle class="accent-dot" cx="36" cy="52" r="8" />
      </g>
      <!-- wrench -->
      <g v-else-if="name === 'wrench'">
        <path class="fill-soft" d="M70 28c12 0 22 10 22 22 0 4-1 8-3 11L58 92c-3 3-8 3-11 0l-8-8c-3-3-3-8 0-11l31-31c3-2 7-3 11-3z" />
        <path class="stroke" d="M78 36c6 6 6 16 0 22M42 78l-8 8" fill="none" />
        <circle class="accent-dot" cx="82" cy="42" r="5" />
      </g>
      <!-- chip -->
      <g v-else-if="name === 'chip'">
        <rect class="fill-soft" x="36" y="36" width="48" height="48" rx="6" />
        <rect class="stroke" x="44" y="44" width="32" height="32" rx="3" fill="none" />
        <g class="accent">
          <path d="M44 28v8M60 28v8M76 28v8M44 84v8M60 84v8M76 84v8M28 44h8M28 60h8M28 76h8M84 44h8M84 60h8M84 76h8" />
        </g>
      </g>
      <!-- calendar -->
      <g v-else-if="name === 'calendar'">
        <rect class="fill-soft" x="24" y="30" width="72" height="68" rx="8" />
        <path class="stroke" d="M24 48h72M40 22v16M80 22v16" fill="none" />
        <circle class="accent-dot" cx="44" cy="68" r="5" />
        <circle class="accent-dot" cx="60" cy="68" r="5" />
        <circle class="accent-dot" cx="76" cy="68" r="5" />
      </g>
      <!-- pin -->
      <g v-else-if="name === 'pin'">
        <path class="fill-soft" d="M60 20c18 0 32 14 32 32 0 24-32 52-32 52S28 76 28 52c0-18 14-32 32-32z" />
        <circle class="stroke" cx="60" cy="50" r="12" fill="none" />
        <circle class="accent-dot" cx="60" cy="50" r="5" />
      </g>
      <!-- board -->
      <g v-else-if="name === 'board'">
        <rect class="fill-soft" x="20" y="28" width="80" height="56" rx="4" />
        <path class="stroke" d="M20 28h80v56H20zM48 84v12M72 84v12M40 96h40" fill="none" />
        <path class="accent" d="M34 48h52M34 62h36" />
      </g>
      <!-- bowl -->
      <g v-else-if="name === 'bowl'">
        <path class="fill-soft" d="M22 52c4 28 18 40 38 40s34-12 38-40H22z" />
        <path class="stroke" d="M18 52h84M60 28c8 8 12 16 12 24" fill="none" />
        <circle class="accent-dot" cx="72" cy="36" r="4" />
      </g>
      <!-- cross -->
      <g v-else-if="name === 'cross'">
        <circle class="fill-soft" cx="60" cy="60" r="38" />
        <path class="stroke" d="M60 22a38 38 0 1 1 0 76a38 38 0 1 1 0-76z" fill="none" />
        <path class="accent" d="M60 40v40M40 60h40" stroke-width="8" stroke-linecap="round" />
      </g>
      <!-- car -->
      <g v-else-if="name === 'car'">
        <path class="fill-soft" d="M22 62h76l-8-22H36L22 62z" />
        <path class="stroke" d="M18 62h84v18H18zM36 40h40l12 22H28z" fill="none" />
        <circle class="accent-dot" cx="38" cy="84" r="8" />
        <circle class="accent-dot" cx="82" cy="84" r="8" />
      </g>
      <!-- door -->
      <g v-else-if="name === 'door'">
        <rect class="fill-soft" x="34" y="20" width="52" height="80" rx="4" />
        <path class="stroke" d="M34 20h52v80H34z" fill="none" />
        <circle class="accent-dot" cx="72" cy="62" r="4" />
      </g>
      <!-- scissors -->
      <g v-else-if="name === 'scissors'">
        <circle class="stroke" cx="36" cy="36" r="12" fill="none" />
        <circle class="stroke" cx="36" cy="84" r="12" fill="none" />
        <path class="accent" d="M46 42l50 40M46 78l50-40" />
        <circle class="fill-soft" cx="36" cy="36" r="5" />
        <circle class="fill-soft" cx="36" cy="84" r="5" />
      </g>
      <!-- key -->
      <g v-else-if="name === 'key'">
        <circle class="fill-soft" cx="40" cy="60" r="22" />
        <circle class="stroke" cx="40" cy="60" r="14" fill="none" />
        <path class="accent" d="M52 60h48v10H88v10H76V70H52z" />
      </g>
      <!-- film -->
      <g v-else-if="name === 'film'">
        <rect class="fill-soft" x="28" y="24" width="64" height="72" rx="4" />
        <path class="stroke" d="M40 24v72M80 24v72M28 40h12M28 56h12M28 72h12M80 40h12M80 56h12M80 72h12" fill="none" />
        <rect class="accent-dot" x="48" y="44" width="24" height="32" rx="2" />
      </g>
      <!-- note -->
      <g v-else-if="name === 'note'">
        <path class="fill-soft" d="M48 28h40v12H60v40c0 10-8 18-18 18s-18-8-18-18 8-18 18-18c4 0 8 1 10 3V28z" />
        <circle class="accent-dot" cx="42" cy="80" r="12" />
        <path class="stroke" d="M60 40h28" fill="none" />
      </g>
      <!-- grid default -->
      <g v-else>
        <rect class="fill-soft" x="22" y="22" width="76" height="76" rx="12" />
        <path class="stroke" d="M22 60h76M60 22v76" fill="none" />
        <circle class="accent-dot" cx="40" cy="40" r="6" />
        <circle class="accent-dot" cx="80" cy="80" r="6" />
      </g>
    </svg>
  </div>
</template>

<script setup>
defineProps({
  name: { type: String, default: 'grid' },
})
</script>

<style scoped>
.motif {
  width: 120px;
  height: 120px;
  margin: 0 auto;
  border-radius: var(--portal-radius-lg, 28px);
  background:
    radial-gradient(circle at 30% 20%, var(--portal-accent-soft, #d7eef0), transparent 55%),
    var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
  box-shadow: var(--portal-shadow, none);
  display: grid;
  place-items: center;
}
.motif-svg {
  width: 88px;
  height: 88px;
  overflow: visible;
}
.fill-soft {
  fill: var(--portal-accent-soft, #d7eef0);
}
.stroke {
  stroke: var(--portal-brand, #08545a);
  stroke-width: 3.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.accent {
  stroke: var(--portal-accent, #0b6e75);
  stroke-width: 3.5;
  stroke-linecap: round;
  fill: none;
}
.accent-dot {
  fill: var(--portal-accent, #0b6e75);
}
</style>

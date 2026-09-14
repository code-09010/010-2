<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Array, default: () => [] },
})

const maxCracked = computed(() => Math.max(1, ...props.stats.map((s) => s.cracked)))
const totalCracked = computed(() => props.stats.reduce((a, s) => a + s.cracked, 0))
const avg = computed(() =>
  props.stats.length ? (totalCracked.value / props.stats.length).toFixed(1) : '0',
)
</script>

<template>
  <section class="card">
    <h2>近十窑开裂情况</h2>
    <p v-if="!stats.length" class="muted">还没有开过窑，烧完一窑这里就有数了。</p>
    <template v-else>
      <div v-for="s in stats" :key="s.firing_id" class="bar-row">
        <router-link class="bar-name" :to="`/firings/${s.firing_id}`">{{ s.name }}</router-link>
        <span class="bar-hold">保温 {{ s.hold_minutes ?? '—' }} 分</span>
        <div class="bar">
          <div class="bar-fill" :style="{ width: (s.cracked / maxCracked) * 100 + '%' }"></div>
        </div>
        <span class="bar-num">
          裂 {{ s.cracked }} / {{ s.total }} 件<template v-if="s.glaze_crawl"> · 缩 {{ s.glaze_crawl }}</template>
        </span>
      </div>
      <p class="muted summary">
        近 {{ stats.length }} 窑共开裂 {{ totalCracked }} 件，平均每窑 {{ avg }} 件。
        开裂偏多时，下一窑考虑把保温段加长些。
      </p>
    </template>
  </section>
</template>

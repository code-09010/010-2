<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  stats: { type: Array, default: () => [] },
  byKiln: { type: Array, default: () => [] },
})

const mode = ref('firing') // firing 按窑次 / kiln 按窑炉

const maxCracked = computed(() => Math.max(1, ...props.stats.map((s) => s.cracked)))
const totalCracked = computed(() => props.stats.reduce((a, s) => a + s.cracked, 0))
const avg = computed(() =>
  props.stats.length ? (totalCracked.value / props.stats.length).toFixed(1) : '0',
)

const maxKilnCracked = computed(() => Math.max(1, ...props.byKiln.map((g) => g.cracked)))
const kilnTotalCracked = computed(() => props.byKiln.reduce((a, g) => a + g.cracked, 0))

function rate(g) {
  return g.total ? ((g.cracked / g.total) * 100).toFixed(0) + '%' : '—'
}
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2>{{ mode === 'firing' ? '近十窑开裂情况' : '各窑炉开裂情况' }}</h2>
      <div class="stat-toggle">
        <button :class="{ on: mode === 'firing' }" @click="mode = 'firing'">按窑次</button>
        <button :class="{ on: mode === 'kiln' }" @click="mode = 'kiln'">按窑炉</button>
      </div>
    </div>

    <template v-if="mode === 'firing'">
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
    </template>

    <template v-else>
      <p v-if="!byKiln.length" class="muted">还没有开过窑，烧完一窑这里就有数了。</p>
      <template v-else>
        <div v-for="g in byKiln" :key="g.kiln_id ?? g.kiln_name" class="bar-row">
          <span class="bar-name">{{ g.kiln_name }}</span>
          <span class="bar-hold">开 {{ g.opened_count }} 窑</span>
          <div class="bar">
            <div class="bar-fill" :style="{ width: (g.cracked / maxKilnCracked) * 100 + '%' }"></div>
          </div>
          <span class="bar-num">
            裂 {{ g.cracked }} / {{ g.total }} 件 · {{ rate(g)
            }}<template v-if="g.glaze_crawl"> · 缩 {{ g.glaze_crawl }}</template>
          </span>
        </div>
        <p class="muted summary">
          各窑炉累计开裂 {{ kilnTotalCracked }} 件。哪口窑裂得多，下一窑装窑和保温就得多留心。
        </p>
      </template>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { PHASE_ORDER } from '../labels'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  readings: { type: Array, default: () => [] },
  startedAt: { type: String, default: null },
})

const W = 640
const H = 280
const PL = 48
const PR = 16
const PT = 16
const PB = 32

// 目标曲线：从常温出发，逐段（升温→保温→降温）累计分钟数
const targetPts = computed(() => {
  const segs = PHASE_ORDER.map((p) => props.segments.find((s) => s.phase === p)).filter(Boolean)
  if (!segs.length) return []
  const pts = [{ t: 0, temp: 25 }]
  let t = 0
  for (const s of segs) {
    t += s.minutes
    pts.push({ t, temp: s.target_temp })
  }
  return pts
})

// 实际看火：相对点火时间的分钟数
const actualPts = computed(() => {
  if (!props.startedAt) return []
  const t0 = new Date(props.startedAt).getTime()
  return props.readings
    .map((r) => ({ t: (new Date(r.recorded_at).getTime() - t0) / 60000, temp: r.temperature }))
    .filter((p) => p.t >= 0)
    .sort((a, b) => a.t - b.t)
})

const maxT = computed(() =>
  Math.max(60, ...targetPts.value.map((p) => p.t), ...actualPts.value.map((p) => p.t)) * 1.05,
)
const maxTemp = computed(() => {
  const m = Math.max(100, ...targetPts.value.map((p) => p.temp), ...actualPts.value.map((p) => p.temp))
  return Math.ceil((m * 1.1) / 100) * 100
})

const x = (t) => PL + (t / maxT.value) * (W - PL - PR)
const y = (temp) => PT + (1 - temp / maxTemp.value) * (H - PT - PB)

const toPath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.temp).toFixed(1)}`).join(' ')
const targetPath = computed(() => toPath(targetPts.value))
const actualPath = computed(() => toPath(actualPts.value))

const yTicks = computed(() => {
  const out = []
  for (let i = 0; i <= 4; i++) out.push(Math.round((maxTemp.value / 4) * i))
  return out
})
const xTicks = computed(() => {
  const out = []
  for (let i = 0; i <= 5; i++) out.push(Math.round((maxT.value / 5) * i))
  return out
})
const empty = computed(() => !targetPts.value.length && !actualPts.value.length)
</script>

<template>
  <div class="chart-wrap">
    <p v-if="empty" class="muted">填好三段曲线后这里会画出目标曲线；烧窑中补的看火温度也会叠上来。</p>
    <svg v-else :viewBox="`0 0 ${W} ${H}`" class="chart" role="img" aria-label="烧成曲线">
      <g v-for="t in yTicks" :key="'y' + t">
        <line :x1="PL" :x2="W - PR" :y1="y(t)" :y2="y(t)" class="grid" />
        <text :x="PL - 6" :y="y(t) + 4" class="tick" text-anchor="end">{{ t }}</text>
      </g>
      <g v-for="t in xTicks" :key="'x' + t">
        <text :x="x(t)" :y="H - 10" class="tick" text-anchor="middle">{{ t }}分</text>
      </g>
      <path v-if="targetPts.length" :d="targetPath" class="line-target" />
      <path v-if="actualPts.length" :d="actualPath" class="line-actual" />
      <circle
        v-for="(p, i) in actualPts"
        :key="i"
        :cx="x(p.t)"
        :cy="y(p.temp)"
        r="3.5"
        class="dot"
      />
      <g>
        <line :x1="W - 200" :x2="W - 178" y1="14" y2="14" class="line-target" />
        <text :x="W - 172" y="18" class="tick">目标曲线</text>
        <line :x1="W - 110" :x2="W - 88" y1="14" y2="14" class="line-actual" />
        <text :x="W - 82" y="18" class="tick">看火实测</text>
      </g>
    </svg>
  </div>
</template>

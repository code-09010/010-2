<script setup>
import { computed, reactive, watch } from 'vue'
import { LABELS, PHASE_ORDER } from '../labels'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['save'])

const rows = reactive(PHASE_ORDER.map((phase) => ({ phase, target_temp: null, minutes: null })))

watch(
  () => props.segments,
  (segs) => {
    for (const row of rows) {
      const found = segs.find((s) => s.phase === row.phase)
      row.target_temp = found ? found.target_temp : null
      row.minutes = found ? found.minutes : null
    }
  },
  { immediate: true },
)

const filled = (v) => v !== null && v !== '' && !Number.isNaN(v)
const valid = computed(() => rows.every((r) => filled(r.target_temp) && filled(r.minutes)))
const totalMinutes = computed(() => rows.reduce((a, r) => a + (Number(r.minutes) || 0), 0))

function save() {
  emit(
    'save',
    rows.map((r) => ({
      phase: r.phase,
      target_temp: Number(r.target_temp),
      minutes: Number(r.minutes),
    })),
  )
}
</script>

<template>
  <div>
    <div class="curve-rows">
      <div v-for="row in rows" :key="row.phase" class="curve-row">
        <span class="phase-label">{{ LABELS.phase[row.phase] }}</span>
        <label>
          目标温度
          <input
            type="number"
            v-model.number="row.target_temp"
            min="0"
            max="1800"
            placeholder="℃"
            :disabled="disabled"
          />
        </label>
        <span class="unit">℃</span>
        <label>
          时长
          <input
            type="number"
            v-model.number="row.minutes"
            min="0"
            placeholder="分钟"
            :disabled="disabled"
          />
        </label>
        <span class="unit">分钟</span>
      </div>
    </div>
    <div class="curve-foot">
      <span class="muted small">
        全程约 {{ Math.floor(totalMinutes / 60) }} 小时 {{ totalMinutes % 60 }} 分
      </span>
      <button v-if="!disabled" class="btn btn-primary btn-sm" :disabled="!valid" @click="save">
        保存曲线
      </button>
    </div>
  </div>
</template>

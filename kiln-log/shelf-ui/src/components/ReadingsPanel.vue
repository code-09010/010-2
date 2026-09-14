<script setup>
import { computed, ref } from 'vue'
import { api } from '../api'

const props = defineProps({
  firingId: { type: Number, required: true },
  status: { type: String, required: true },
  startedAt: { type: String, default: null },
  readings: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh', 'error'])

const temp = ref(null)
const note = ref('')
const when = ref('') // 补记用，可空
const busy = ref(false)

const sorted = computed(() =>
  [...props.readings].sort((a, b) => new Date(b.recorded_at) - new Date(a.recorded_at)),
)

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}
function elapsed(r) {
  if (!props.startedAt) return '—'
  const mins = Math.round((new Date(r.recorded_at) - new Date(props.startedAt)) / 60000)
  if (mins < 0) return '—'
  return mins < 60 ? `${mins} 分` : `${Math.floor(mins / 60)} 时 ${mins % 60} 分`
}

async function add() {
  if (temp.value === null || temp.value === '') return
  busy.value = true
  try {
    const data = { temperature: Number(temp.value), note: note.value }
    if (when.value) data.recorded_at = new Date(when.value).toISOString()
    await api.addReading(props.firingId, data)
    temp.value = null
    note.value = ''
    when.value = ''
    emit('refresh')
  } catch (e) {
    emit('error', e.message)
  } finally {
    busy.value = false
  }
}

async function remove(id) {
  try {
    await api.deleteReading(id)
    emit('refresh')
  } catch (e) {
    emit('error', e.message)
  }
}
</script>

<template>
  <section class="card">
    <h2>看火记录</h2>
    <form v-if="status === 'firing'" class="reading-form" @submit.prevent="add">
      <input type="number" v-model.number="temp" min="0" max="1800" placeholder="实际温度 ℃" required />
      <input type="text" v-model="note" placeholder="备注（火色、闸板、可空）" maxlength="200" />
      <input type="datetime-local" v-model="when" title="补记时间，留空就是现在" />
      <button class="btn btn-primary" :disabled="busy">记一笔</button>
    </form>
    <p v-else-if="status === 'planned'" class="muted">点火后在这里补实际看火温度。</p>
    <p v-if="!readings.length" class="muted">还没有看火记录。</p>
    <table v-else class="tbl">
      <thead>
        <tr><th>时间</th><th>点火后</th><th>温度</th><th>备注</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in sorted" :key="r.id">
          <td>{{ fmt(r.recorded_at) }}</td>
          <td>{{ elapsed(r) }}</td>
          <td class="temp">{{ r.temperature }} ℃</td>
          <td>{{ r.note }}</td>
          <td><button class="btn btn-ghost btn-sm" @click="remove(r.id)">删</button></td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

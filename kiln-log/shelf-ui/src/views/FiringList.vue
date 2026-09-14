<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { LABELS } from '../labels'
import CrackStats from '../components/CrackStats.vue'

const router = useRouter()
const firings = ref([])
const stats = ref([])
const kilnStats = ref([])
const kilns = ref([])
const error = ref('')
const showForm = ref(false)
const busy = ref(false)

const form = ref({
  name: '',
  kiln_id: null,
  atmosphere: 'oxidation',
  shelf_layers: null,
  slots_per_layer: null,
  note: '',
})

async function load() {
  try {
    ;[firings.value, stats.value, kilnStats.value, kilns.value] = await Promise.all([
      api.listFirings(),
      api.crackStats(),
      api.crackStatsByKiln(),
      api.listKilns(),
    ])
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

const pickedKiln = computed(() => kilns.value.find((k) => k.id === form.value.kiln_id) || null)

// 选了窑就把档案规格带出来；手改过数字就是临时覆盖，给提示
function applyKiln() {
  if (!pickedKiln.value) return
  form.value.shelf_layers = pickedKiln.value.shelf_layers
  form.value.slots_per_layer = pickedKiln.value.slots_per_layer
}

const overridden = computed(
  () =>
    pickedKiln.value &&
    (form.value.shelf_layers !== pickedKiln.value.shelf_layers ||
      form.value.slots_per_layer !== pickedKiln.value.slots_per_layer),
)

async function create() {
  busy.value = true
  error.value = ''
  try {
    const f = await api.createFiring(form.value)
    router.push(`/firings/${f.id}`)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div v-if="error" class="error-banner">{{ error }}</div>

  <CrackStats :stats="stats" :by-kiln="kilnStats" />

  <section class="card">
    <div class="card-head">
      <h2>窑次</h2>
      <button class="btn btn-primary" @click="showForm = !showForm">
        {{ showForm ? '收起' : '新窑次' }}
      </button>
    </div>

    <form v-if="showForm" class="create-form" @submit.prevent="create">
      <div class="meta-grid">
        <label>窑次名<input v-model="form.name" required placeholder="如：第 12 窑 · 釉烧" /></label>
        <label>
          窑炉
          <select v-model="form.kiln_id" required @change="applyKiln">
            <option :value="null" disabled>选一口窑</option>
            <option v-for="k in kilns" :key="k.id" :value="k.id">
              {{ k.name }}（{{ k.shelf_layers }} 层 × {{ k.slots_per_layer }} 位）
            </option>
          </select>
        </label>
        <label>
          气氛
          <select v-model="form.atmosphere">
            <option value="oxidation">氧化</option>
            <option value="reduction">还原</option>
          </select>
        </label>
        <label>棚板层数<input type="number" v-model.number="form.shelf_layers" min="1" max="12" required /></label>
        <label>每层窑位<input type="number" v-model.number="form.slots_per_layer" min="1" max="24" required /></label>
        <label>备注<input v-model="form.note" placeholder="可空" /></label>
      </div>
      <p v-if="!kilns.length" class="muted small">
        还没有窑炉档案，先到 <router-link to="/kilns">窑炉档案</router-link> 建一口窑。
      </p>
      <p v-else-if="overridden" class="override-hint">
        层数/窑位与「{{ pickedKiln.name }}」的档案规格（{{ pickedKiln.shelf_layers }} 层 ×
        {{ pickedKiln.slots_per_layer }} 位）不一致，这次按手改的烧，档案不动。
      </p>
      <button class="btn btn-primary" :disabled="busy || !form.kiln_id">建窑次</button>
    </form>

    <p v-if="!firings.length" class="muted">还没有窑次，点「新窑次」开第一窑。</p>
    <table v-else class="tbl">
      <thead>
        <tr><th>窑次</th><th>气氛</th><th>状态</th><th>坯件</th><th>建窑时间</th></tr>
      </thead>
      <tbody>
        <tr v-for="f in firings" :key="f.id" class="row-link" @click="router.push(`/firings/${f.id}`)">
          <td><strong>{{ f.name }}</strong> <span class="muted">{{ f.kiln_name }}</span></td>
          <td>
            <span class="badge" :class="f.atmosphere === 'reduction' ? 'b-red' : 'b-ox'">
              {{ LABELS.atmosphere[f.atmosphere] }}
            </span>
          </td>
          <td><span class="badge" :class="'b-' + f.status">{{ LABELS.status[f.status] }}</span></td>
          <td>
            <template v-if="f.status === 'opened'">
              成品 {{ f.good }} · 裂 {{ f.cracked }} · 缩 {{ f.glaze_crawl
              }}<template v-if="f.unresulted"> · 待登记 {{ f.unresulted }}</template>
            </template>
            <template v-else>已摆 {{ f.placed }} / {{ f.piece_total }} 件</template>
          </td>
          <td class="muted">{{ fmt(f.created_at) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { LABELS } from '../labels'
import CrackStats from '../components/CrackStats.vue'

const router = useRouter()
const firings = ref([])
const stats = ref([])
const error = ref('')
const showForm = ref(false)
const busy = ref(false)

const form = ref({
  name: '',
  kiln_name: '主窑',
  atmosphere: 'oxidation',
  shelf_layers: 4,
  slots_per_layer: 6,
  note: '',
})

async function load() {
  try {
    ;[firings.value, stats.value] = await Promise.all([api.listFirings(), api.crackStats()])
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

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

  <CrackStats :stats="stats" />

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
        <label>窑炉<input v-model="form.kiln_name" /></label>
        <label>
          气氛
          <select v-model="form.atmosphere">
            <option value="oxidation">氧化</option>
            <option value="reduction">还原</option>
          </select>
        </label>
        <label>棚板层数<input type="number" v-model.number="form.shelf_layers" min="1" max="12" /></label>
        <label>每层窑位<input type="number" v-model.number="form.slots_per_layer" min="1" max="24" /></label>
        <label>备注<input v-model="form.note" placeholder="可空" /></label>
      </div>
      <button class="btn btn-primary" :disabled="busy">建窑次</button>
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

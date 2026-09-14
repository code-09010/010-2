<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const kilns = ref([])
const error = ref('')
const busy = ref(false)

const blank = { name: '', shelf_layers: 4, slots_per_layer: 6, note: '' }
const form = ref({ ...blank })
const editingId = ref(null) // 在改哪一口；null = 新增
const mergingId = ref(null) // 删除时名下还有窑次、展开「并给」的那口窑
const mergeTarget = ref('')

async function load() {
  try {
    kilns.value = await api.listKilns()
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

const mergeCandidates = computed(() => kilns.value.filter((k) => k.id !== mergingId.value))

function resetForm() {
  editingId.value = null
  form.value = { ...blank }
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await api.patchKiln(editingId.value, form.value)
    } else {
      await api.createKiln(form.value)
    }
    resetForm()
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function edit(k) {
  mergingId.value = null
  editingId.value = k.id
  form.value = {
    name: k.name,
    shelf_layers: k.shelf_layers,
    slots_per_layer: k.slots_per_layer,
    note: k.note,
  }
}

async function remove(k) {
  error.value = ''
  if (k.firing_count > 0) {
    // 名下有窑次，得先选一口窑把窑次并过去
    mergingId.value = k.id
    mergeTarget.value = ''
    return
  }
  if (!confirm(`删掉「${k.name}」的档案？`)) return
  try {
    await api.deleteKiln(k.id)
    if (editingId.value === k.id) resetForm()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function mergeRemove(k) {
  if (!mergeTarget.value) return
  error.value = ''
  try {
    await api.deleteKiln(k.id, Number(mergeTarget.value))
    mergingId.value = null
    if (editingId.value === k.id) resetForm()
    await load()
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div v-if="error" class="error-banner">{{ error }}</div>

  <section class="card">
    <div class="card-head">
      <h2>窑炉档案</h2>
    </div>
    <p class="muted small">
      每口窑的棚板层数、每层窑位是固定规格，建窑次时选窑自动带出。
      改规格只影响之后新建的窑次，已经在册的窑次不动。
    </p>

    <form class="create-form" @submit.prevent="save">
      <div class="meta-grid">
        <label>窑名<input v-model="form.name" required placeholder="如：气窑" /></label>
        <label>棚板层数<input type="number" v-model.number="form.shelf_layers" min="1" max="12" required /></label>
        <label>每层窑位<input type="number" v-model.number="form.slots_per_layer" min="1" max="24" required /></label>
        <label>备注<input v-model="form.note" placeholder="可空" /></label>
      </div>
      <button class="btn btn-primary" :disabled="busy">{{ editingId ? '保存修改' : '建档' }}</button>
      <button v-if="editingId" type="button" class="btn btn-ghost" @click="resetForm">取消</button>
    </form>

    <p v-if="!kilns.length" class="muted">还没有档案，先在上面建一口窑。</p>
    <table v-else class="tbl">
      <thead>
        <tr><th>窑名</th><th>规格</th><th>窑次数</th><th>备注</th><th></th></tr>
      </thead>
      <tbody>
        <template v-for="k in kilns" :key="k.id">
          <tr>
            <td><strong>{{ k.name }}</strong></td>
            <td>{{ k.shelf_layers }} 层 × 每层 {{ k.slots_per_layer }} 位</td>
            <td>{{ k.firing_count }} 窑</td>
            <td class="muted">{{ k.note || '—' }}</td>
            <td class="kiln-ops">
              <button class="btn btn-sm" @click="edit(k)">编辑</button>
              <button class="btn btn-danger btn-sm" @click="remove(k)">删除</button>
            </td>
          </tr>
          <tr v-if="mergingId === k.id" class="merge-row">
            <td colspan="5">
              「{{ k.name }}」名下还有 {{ k.firing_count }} 窑，删掉前把这些窑并给：
              <select v-model="mergeTarget">
                <option value="" disabled>选一口窑</option>
                <option v-for="c in mergeCandidates" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <button class="btn btn-primary btn-sm" :disabled="!mergeTarget" @click="mergeRemove(k)">
                并档后删除
              </button>
              <button class="btn btn-ghost btn-sm" @click="mergingId = null">算了</button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>

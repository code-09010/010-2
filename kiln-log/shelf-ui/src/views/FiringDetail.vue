<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { LABELS, RESULT_ORDER } from '../labels'
import ShelfMap from '../components/ShelfMap.vue'
import CurveEditor from '../components/CurveEditor.vue'
import CurveChart from '../components/CurveChart.vue'
import ReadingsPanel from '../components/ReadingsPanel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const fid = Number(props.id)

const firing = ref(null)
const kilns = ref([])
const error = ref('')
const selectedId = ref(null) // 待摆坯件里被点中的
const newPiece = ref('')
const meta = ref(null) // 第一次载入后接住表单，之后不被刷新覆盖

async function load() {
  try {
    const f = await api.getFiring(fid)
    firing.value = f
    if (!meta.value) {
      meta.value = {
        name: f.name,
        kiln_id: f.kiln_id,
        atmosphere: f.atmosphere,
        note: f.note,
        shelf_layers: f.shelf_layers,
        slots_per_layer: f.slots_per_layer,
      }
    }
  } catch (e) {
    error.value = e.message
  }
}
onMounted(() => {
  load()
  api.listKilns().then((ks) => (kilns.value = ks)).catch((e) => (error.value = e.message))
})

// 包一层：调接口、报错上墙、成功后重载
function guard(fn) {
  return async (...args) => {
    error.value = ''
    try {
      await fn(...args)
      await load()
    } catch (e) {
      error.value = e.message
    }
  }
}

const saveMeta = guard(async () => {
  await api.patchFiring(fid, meta.value)
})

const start = guard(async () => {
  const f = firing.value
  const warn = []
  if (!f.pieces.some((p) => p.shelf_layer)) warn.push('还没摆坯件')
  if (f.segments.length < 3) warn.push('曲线还没填全')
  if (warn.length && !confirm(`${warn.join('、')}，仍要点火吗？`)) return
  await api.startFiring(fid)
})

const open = guard(async () => {
  if (confirm('确认开窑？开窑后窑位和曲线就定档了。')) await api.openFiring(fid)
})

const removeFiring = guard(async () => {
  if (!confirm('删掉这一窑？坯件、曲线、看火记录都会一起删掉。')) return
  await api.deleteFiring(fid)
  router.push('/')
})

const saveCurve = guard(async (segments) => api.putCurve(fid, segments))

const addPiece = guard(async () => {
  if (!newPiece.value.trim()) return
  await api.addPiece(fid, newPiece.value.trim())
  newPiece.value = ''
})

const removePiece = guard(async (p) => {
  if (confirm(`把「${p.name}」从这窑拿掉？`)) await api.deletePiece(p.id)
})

const onCellClick = guard(async (cell) => {
  if (firing.value.status !== 'planned') return
  if (cell.piece) {
    await api.unplacePiece(cell.piece.id)
    if (selectedId.value === cell.piece.id) selectedId.value = null
  } else if (selectedId.value) {
    await api.placePiece(selectedId.value, cell.layer, cell.slot)
    selectedId.value = null
  }
})

const setResult = guard(async (p, result) => {
  await api.patchPiece(p.id, { result })
})

function toggleSelect(p) {
  if (firing.value.status !== 'planned') return
  selectedId.value = selectedId.value === p.id ? null : p.id
}

const unplaced = computed(() =>
  firing.value ? firing.value.pieces.filter((p) => p.shelf_layer === null) : [],
)
const placed = computed(() =>
  firing.value ? firing.value.pieces.filter((p) => p.shelf_layer !== null) : [],
)
const placedSorted = computed(() =>
  [...placed.value].sort((a, b) => a.shelf_layer - b.shelf_layer || a.slot - b.slot),
)
const resultSummary = computed(() => {
  const s = { good: 0, cracked: 0, glaze_crawl: 0, pending: 0 }
  for (const p of placed.value) s[p.result] = (s[p.result] || 0) + 1
  return s
})
const linkedKiln = computed(
  () => kilns.value.find((k) => k.id === meta.value?.kiln_id) || null,
)
// 层数/窑位被改得和档案规格不一样时提一句：保存只影响这一窑
const specDiverged = computed(
  () =>
    firing.value?.status === 'planned' &&
    linkedKiln.value &&
    (meta.value.shelf_layers !== linkedKiln.value.shelf_layers ||
      meta.value.slots_per_layer !== linkedKiln.value.slots_per_layer),
)
const firingElapsed = computed(() => {
  const f = firing.value
  if (!f?.started_at) return ''
  const end = f.opened_at ? new Date(f.opened_at) : new Date()
  const mins = Math.max(0, Math.round((end - new Date(f.started_at)) / 60000))
  return `${Math.floor(mins / 60)} 小时 ${mins % 60} 分`
})

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div v-if="error" class="error-banner">{{ error }}</div>
  <p v-if="!firing" class="muted">载入中…</p>
  <template v-else>
    <section class="card">
      <div class="firing-head">
        <div class="firing-title">
          <input v-model="meta.name" class="name-input" />
          <span class="badge" :class="'b-' + firing.status">{{ LABELS.status[firing.status] }}</span>
        </div>
        <div class="firing-actions">
          <button v-if="firing.status === 'planned'" class="btn btn-primary" @click="start">点火开烧</button>
          <button v-if="firing.status === 'firing'" class="btn btn-primary" @click="open">开窑</button>
          <button class="btn btn-danger btn-sm" @click="removeFiring">删除</button>
        </div>
      </div>
      <div class="meta-grid">
        <label>
          窑炉
          <select v-model="meta.kiln_id">
            <option :value="null">未挂档案</option>
            <option v-for="k in kilns" :key="k.id" :value="k.id">{{ k.name }}</option>
          </select>
        </label>
        <label>
          气氛
          <select v-model="meta.atmosphere">
            <option value="oxidation">氧化</option>
            <option value="reduction">还原</option>
          </select>
        </label>
        <template v-if="firing.status === 'planned'">
          <label>棚板层数<input type="number" min="1" max="12" v-model.number="meta.shelf_layers" /></label>
          <label>每层窑位<input type="number" min="1" max="24" v-model.number="meta.slots_per_layer" /></label>
        </template>
        <label class="meta-note">备注<input v-model="meta.note" placeholder="如：釉烧、昨晚那炉" /></label>
        <div><button class="btn btn-sm" @click="saveMeta">保存信息</button></div>
      </div>
      <p v-if="specDiverged" class="override-hint">
        层数/窑位与「{{ linkedKiln.name }}」的档案规格（{{ linkedKiln.shelf_layers }} 层 ×
        {{ linkedKiln.slots_per_layer }} 位）不一致，保存只改这一窑，档案不动。
      </p>
      <p class="muted times">
        建于 {{ fmt(firing.created_at) }}
        <template v-if="firing.started_at"> · 点火 {{ fmt(firing.started_at) }}</template>
        <template v-if="firing.opened_at"> · 开窑 {{ fmt(firing.opened_at) }}</template>
        <template v-if="firing.started_at"> · 共烧 {{ firingElapsed }}</template>
      </p>
    </section>

    <section class="card">
      <h2>烧成曲线 <span class="muted small">升温 / 保温 / 降温三段</span></h2>
      <CurveEditor
        :segments="firing.segments"
        :disabled="firing.status === 'opened'"
        @save="saveCurve"
      />
      <CurveChart
        :segments="firing.segments"
        :readings="firing.readings"
        :started-at="firing.started_at"
      />
    </section>

    <section class="card">
      <h2>
        窑位图
        <span class="muted small">{{ firing.shelf_layers }} 层棚板 × 每层 {{ firing.slots_per_layer }} 位</span>
      </h2>
      <template v-if="firing.status === 'planned'">
        <form class="add-piece" @submit.prevent="addPiece">
          <input v-model="newPiece" placeholder="坯件名字，如：青花盖碗 #12" maxlength="120" />
          <button class="btn">添坯件</button>
        </form>
        <div v-if="unplaced.length" class="chips">
          <span class="muted">待摆：</span>
          <button
            v-for="p in unplaced"
            :key="p.id"
            class="chip"
            :class="{ on: p.id === selectedId }"
            @click="toggleSelect(p)"
          >
            {{ p.name }}
            <span class="chip-x" @click.stop="removePiece(p)">✕</span>
          </button>
        </div>
        <p class="muted small">点一个待摆坯件，再点图上的空窑位；点已摆的坯件可把它撤下来。</p>
      </template>
      <ShelfMap
        :layers="firing.shelf_layers"
        :slots="firing.slots_per_layer"
        :pieces="placed"
        :interactive="firing.status === 'planned'"
        @cell-click="onCellClick"
      />
      <p v-if="firing.status !== 'planned' && !placed.length" class="muted">这窑没有摆坯件。</p>
    </section>

    <ReadingsPanel
      :firing-id="firing.id"
      :status="firing.status"
      :started-at="firing.started_at"
      :readings="firing.readings"
      @refresh="load"
      @error="(e) => (error = e)"
    />

    <section v-if="firing.status === 'opened'" class="card">
      <h2>开窑结果</h2>
      <p class="result-summary">
        <span class="badge r-good">成品 {{ resultSummary.good }}</span>
        <span class="badge r-cracked">开裂 {{ resultSummary.cracked }}</span>
        <span class="badge r-glaze_crawl">釉缩 {{ resultSummary.glaze_crawl }}</span>
        <span v-if="resultSummary.pending" class="badge">待登记 {{ resultSummary.pending }}</span>
      </p>
      <table v-if="placedSorted.length" class="tbl">
        <thead>
          <tr><th>窑位</th><th>坯件</th><th>结果</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in placedSorted" :key="p.id">
            <td>第 {{ p.shelf_layer }} 层 · {{ p.slot }} 号</td>
            <td>{{ p.name }}</td>
            <td class="result-btns">
              <button
                v-for="r in RESULT_ORDER"
                :key="r"
                class="btn btn-sm"
                :class="['rb-' + r, { active: p.result === r }]"
                @click="setResult(p, r)"
              >
                {{ LABELS.result[r] }}
              </button>
              <button v-if="p.result !== 'pending'" class="btn btn-ghost btn-sm" @click="setResult(p, 'pending')">
                清除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">这窑没有入窑的坯件。</p>
    </section>
  </template>
</template>

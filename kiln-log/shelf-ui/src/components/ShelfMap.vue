<script setup>
import { computed } from 'vue'
import { LABELS } from '../labels'

const props = defineProps({
  layers: { type: Number, required: true },
  slots: { type: Number, required: true },
  pieces: { type: Array, default: () => [] },
  interactive: { type: Boolean, default: false },
})
const emit = defineEmits(['cell-click'])

// 图上最高层在最上面，第一层棚板压底
const grid = computed(() => {
  const byPos = new Map(props.pieces.map((p) => [`${p.shelf_layer}-${p.slot}`, p]))
  const rows = []
  for (let layer = props.layers; layer >= 1; layer--) {
    const cells = []
    for (let slot = 1; slot <= props.slots; slot++) {
      cells.push({ layer, slot, piece: byPos.get(`${layer}-${slot}`) || null })
    }
    rows.push({ layer, cells })
  }
  return rows
})
</script>

<template>
  <div class="shelf-map">
    <div v-for="row in grid" :key="row.layer" class="shelf-layer">
      <div class="layer-label">第{{ row.layer }}层</div>
      <div class="slot-grid" :style="{ gridTemplateColumns: `repeat(${slots}, minmax(64px, 1fr))` }">
        <button
          v-for="cell in row.cells"
          :key="cell.slot"
          class="slot"
          :class="{
            filled: cell.piece,
            interactive,
            ['r-' + cell.piece?.result]: cell.piece,
          }"
          @click="emit('cell-click', cell)"
        >
          <template v-if="cell.piece">
            <span class="slot-name">{{ cell.piece.name }}</span>
            <span v-if="cell.piece.result !== 'pending'" class="slot-result">
              {{ LABELS.result[cell.piece.result] }}
            </span>
          </template>
          <span v-else class="slot-empty">{{ cell.layer }}-{{ cell.slot }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

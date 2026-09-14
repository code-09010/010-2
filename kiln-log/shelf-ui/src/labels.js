export const LABELS = {
  atmosphere: { oxidation: '氧化', reduction: '还原' },
  status: { planned: '待烧', firing: '烧窑中', opened: '已开窑' },
  phase: { heat: '升温', hold: '保温', cool: '降温' },
  result: { pending: '待登记', good: '成品', cracked: '开裂', glaze_crawl: '釉缩' },
}

export const PHASE_ORDER = ['heat', 'hold', 'cool']
export const RESULT_ORDER = ['good', 'cracked', 'glaze_crawl']

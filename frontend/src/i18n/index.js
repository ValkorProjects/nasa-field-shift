// Minimal i18n: t('nav.farm'). Add pt.json later and switch `locale`.
import { ref } from 'vue'
import en from './en.json'

const messages = { en }
export const locale = ref('en')

export function t(key) {
  const out = key.split('.').reduce((o, k) => (o == null ? o : o[k]), messages[locale.value])
  return out ?? key
}

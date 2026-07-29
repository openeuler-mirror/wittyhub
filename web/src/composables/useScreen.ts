import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'

export enum Size {
  Phone = 'phone',
  PadV = 'pad_v',
  PadH = 'pad_h',
  Laptop = 'laptop',
}

export type ScreenSizeT = typeof Size.Phone | Size.PadV | Size.PadH | Size.Laptop

export const ScreenConfig = {
  [Size.Phone]: 600,
  [Size.PadV]: 840,
  [Size.PadH]: 1200,
  [Size.Laptop]: 1440,
}

export type CompareT = 'lt' | 'le' | 'eq' | 'ne' | 'ge' | 'gt'

const CompareHandler = {
  lt: (a: number, b: number) => a < b,
  le: (a: number, b: number) => a <= b,
  eq: (a: number, b: number) => a === b,
  ne: (a: number, b: number) => a !== b,
  ge: (a: number, b: number) => a >= b,
  gt: (a: number, b: number) => a > b,
}

export const useScreen = () => {
  const screenSize = reactive({
    width: 1440,
    height: 0,
  })

  const current = ref<ScreenSizeT>(Size.Laptop)

  const getSize = (width?: number) => {
    if (typeof width === 'undefined') {
      width = screenSize.width
    }
    if (width < ScreenConfig[Size.Phone]) {
      return Size.Phone
    } else if (width < ScreenConfig[Size.PadV]) {
      return Size.PadV
    } else if (width < ScreenConfig[Size.PadH]) {
      return Size.PadH
    } else {
      return Size.Laptop
    }
  }

  const compare = (type: CompareT = 'eq', size: ScreenSizeT) => {
    const w1 = screenSize.width
    const w2 = ScreenConfig[size]
    const handler = CompareHandler[type]
    return handler(w1, w2)
  }

  const isPhone = computed(() => compare('le', Size.Phone))
  const gtPhone = computed(() => compare('gt', Size.Phone))
  const isPad = computed(() => compare('gt', Size.Phone) && compare('le', Size.PadH))
  const lePad = computed(() => compare('le', Size.PadH))
  const gtPad = computed(() => compare('gt', Size.PadH))
  const isPadV = computed(() => compare('gt', Size.Phone) && compare('le', Size.PadV))
  const lePadV = computed(() => compare('le', Size.PadV))
  const gtPadV = computed(() => compare('gt', Size.PadV))
  const isPadH = computed(() => compare('gt', Size.PadV) && compare('le', Size.PadH))
  const isLaptop = computed(() => compare('gt', Size.PadH) && compare('le', Size.Laptop))
  const leLaptop = computed(() => compare('le', Size.Laptop))
  const gtLaptop = computed(() => compare('gt', Size.Laptop))
  const isPadToLaptop = computed(() => compare('gt', Size.Phone) && compare('le', Size.Laptop))
  const isPadVToLaptop = computed(() => compare('gt', Size.PadV) && compare('le', Size.Laptop))

  const onWindowResize = () => {
    const { innerWidth, innerHeight } = window
    screenSize.width = innerWidth
    screenSize.height = innerHeight
    current.value = getSize()
  }

  onMounted(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', onWindowResize)
      onWindowResize()
      nextTick(() => onWindowResize())
    }
  })

  onUnmounted(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', onWindowResize)
    }
  })

  return {
    getSize,
    current,
    size: screenSize,
    isPhone,
    gtPhone,
    isPad,
    lePad,
    gtPad,
    isPadV,
    lePadV,
    gtPadV,
    isPadH,
    isLaptop,
    leLaptop,
    gtLaptop,
    isPadToLaptop,
    isPadVToLaptop,
  }
}

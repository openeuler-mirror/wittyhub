> ← [组件索引](../SKILL.md#组件索引) · [README](../../../README.md)

# OTimePicker 时间选择器

## Part A：设计理解卡

OTimePicker 是时间选择组件，支持时分秒的选择和范围选择。面板由 3 列滚动列表（时/分/秒）组成，继承 InBox 边框系统，依赖 dayjs 运行时。OTimeRangePicker 支持键盘导航（Tab/ArrowLeft/ArrowRight 在两个输入框间切换）。

### 子组件一览

| 子组件 | 选择粒度 | v-model 方式 | 默认 format |
|--------|---------|-------------|------------|
| OTimePicker | 时分秒 | `v-model="val"` | `'HH:mm:ss'` |
| OTimeRangePicker | 时分秒范围 | `v-model:start="s" v-model:end="e"` | `'HH:mm:ss'` |

### 共享基础 Props（两个子组件）

**size**（属性）：尺寸。"large" 大号、"medium" 中号、"small" 小号。继承自 inputProps。

**variant**（属性）：输入框类型。"outline" 有边框轮廓、"solid" 实心填充、"text" 无边框。继承自 inputProps。

**color**（属性）：颜色。"normal" 默认、"success" 成功、"warning" 警告、"danger" 危险。OForm 内自动继承校验状态。

**round**（属性）：圆角值。"pill" 全圆角胶囊形，或 CSS border-radius 值。继承自 inputProps。

**placeholder**（属性）：占位文本。单选使用。继承自 inputProps。

**disabled**（属性）：禁用。继承自 inputProps。

**readonly**（属性）：只读。继承自 inputProps。

**clearable**（属性）：可清空。悬停时显示清除图标替换时间图标。

**format**（属性）：时间格式。支持 dayjs format。"HH:mm:ss"（默认）或 "HH:mm"（仅时分）。format 中不含 ss 时秒列不显示。

### 时间约束 Props

**hourStep**（属性）：小时步进。默认 1。设为 2 时选项为 0, 2, 4, ...22。

**minuteStep**（属性）：分钟步进。默认 1。设为 15 时选项为 0, 15, 30, 45。

**secondStep**（属性）：秒步进。默认 1。

**disabledHours**（属性）：禁用小时函数。返回被禁用的小时数组，如 `[0, 1, 2, 12, 13]`。

**disabledMinutes**（属性）：禁用分钟函数。接收当前小时 `(hour: number)`，返回被禁用的分钟数组。

**disabledSeconds**（属性）：禁用秒函数。接收当前小时和分钟 `(hour: number, minute: number)`，返回被禁用的秒数组。

**minTime**（属性）：最小可选时间。字符串格式如 "09:30:00"。与 disabledHours 等同时设置时约束取并集。

**maxTime**（属性）：最大可选时间。字符串格式如 "18:30:00"。与 disabledHours 等同时设置时约束取并集。

### OTimeRangePicker 专属 Props

**placeholderStart**（属性）：开始时间占位文本。

**placeholderEnd**（属性）：结束时间占位文本。

### 浮层控制 Props

**trigger**（属性）：浮层触发方式。"click"（默认）等 PopupTriggerT 值。

**popupPosition**（属性）：浮层位置。"bl" 左下（默认）等 PopupPositionT 值。

**popupWrapper**（属性）：浮层挂载容器。默认 "body"。

**unmountOnHide**（属性）：关闭时卸载 DOM。默认 true。

**transition**（属性）：浮层过渡动画名称。

**noResponsive**（属性）：是否禁用响应式。继承自 selectProps。

**optionTitle**（属性）：浮层标题。继承自 selectProps。

### 值模式

**OTimePicker**：v-model 绑定值类型为 `string | undefined`，格式由 format prop 决定（如 "14:30:00"）。聚焦时若无值，自动填充最近可用时间（findNearestTime）。输入框可直接输入时间字符串，失焦时校验合法则应用、否则回滚。

**OTimeRangePicker**：v-model:start + v-model:end 双向绑定。仅当 start 和 end 都有值（或都无值）时才触发 change 事件。范围选择器自动计算 minEndTime（结束时间最小值不能小于开始时间）和 maxStartTime（开始时间最大值不能大于结束时间）。支持键盘导航：Tab 在 start/end 输入框间切换、ArrowRight 从 start 末尾跳到 end、ArrowLeft 从 end 开头跳到 start。

### 事件（OTimePicker）

**change**（事件）：值变化，参数 `(newVal: string | undefined, oldVal: string | undefined)`。

**focus**（事件）：获得焦点，参数 `(evt: FocusEvent)`。

**blur**（事件）：失去焦点。

**clear**（事件）：清空，参数 `(evt?: Event)`。

**pressEnter**（事件）：按下回车。

### 事件（OTimeRangePicker）

**change**（事件）：值变化，参数 `(newVal: TimeRangeValue, oldVal: TimeRangeValue)`，TimeRangeValue 为 `{ start: string|undefined, end: string|undefined }`。

**focus**（事件）：获得焦点，参数 `(evt: FocusEvent)`。

**blur**（事件）：两个输入框都失去焦点时触发。

**clear**（事件）：清空。

**pressEnter**（事件）：按下回车（仅两端值合法时触发）。

### 插槽

**prepend**（插槽）：前置内容，InBox prepend 区域。

**append**（插槽）：后置内容，InBox append 区域。

**shortcut**（OTimePicker 插槽）：快捷选项，Slot Props `{ setValue: (value?: string) => void, emitChange: () => void }`。

**shortcut**（OTimeRangePicker 插槽）：快捷选项，Slot Props `{ setValue: (start?: string, end?: string) => void, emitChange: () => void }`。

### 暴露方法

**focus(open?)**（方法）：聚焦输入框。open=true 同时打开面板，open=false 仅聚焦。

**blur()**（方法）：失焦。校验合法则应用值，否则回滚。

**clear()**（方法）：清除值。

**inputEl()**（方法）：获取输入框 DOM 元素（仅 OTimePicker）。

### 运行时依赖

**dayjs**：时间选择器依赖 dayjs 作为运行时库。

📱 **响应式行为**：有 media.scss 断点规则。

- **≤1440px (laptop)**：large 面板时间项字号缩小为 tip1、行高 tip1。
- **触控设备**：面板标记 `.o-time-panel-touch`，时间列显示项数缩小为 5（默认 8）、项高度增大为 48px、无间距、全宽。
- **范围选择器移动端降级**：建议在 pad_v 及以下使用两个独立 OTimePicker 替代 OTimeRangePicker。

🧩 **布局结构**：OTimePicker 根元素为 InBox（继承边框/圆角/颜色/尺寸），内部为 InInput（输入框 + 时间图标 IconTime + 清除按钮 + OPopup 面板）。面板由 TimePanel 渲染，包含 3 列滚动列表（时 OScroller + 分 OScroller + 秒 OScroller）+ footer（确认/取消按钮）+ shortcut 区域。OTimeRangePicker 根元素为 InBox，内部为两个 InInput（start + end）+ 中间分隔线 "-" + 时间图标/清除按钮。
```yaml
# 简化结构摘要
direction(单选): InBox → [prepend | InInput(input+IconTime+clear+TimePanel) | append]
direction(范围): InBox → [prepend | start-InInput | divider(-) | end-InInput | suffix-icon(IconTime/clear) | append]
note: 面板为3列横向排列的时间滚动列表(时/分/秒) + footer(确认取消) + shortcut(可选)
```

🔍 **设计稿识别指南**：
- **视觉特征指纹**：输入框 + 右侧时钟图标（IconTime）+ 点击后弹出 3 列时间滚动列表面板
- **3列时间面板**：左列小时、中间列分钟、右列秒 → 匹配 format="HH:mm:ss"；2 列（无秒列） → format="HH:mm"
- **范围选择器**：两个输入框 + 中间 "-" 分隔 + 时钟图标 → OTimeRangePicker
- **步进模式**：时间列中选项间隔有规律（如小时列只显示 0,2,4...） → hourStep/minuteStep/secondStep
- **Token → Prop 映射**：时钟图标在输入框右侧=固定; 有边框=variant:outline; 胶囊圆角=round:pill; 大号=size:large; 清除按钮=clearable:true; 禁用=disabled:true; 红色边框=color:danger(OForm内自动); 格式HH:mm=format:'HH:mm'(无秒列); 步进间隔=hourStep/minuteStep/secondStep
- **易混淆组件区分**：与 ODatePicker 区别——TimePicker 面板是 3 列时间滚动列表，DatePicker 面板是日历网格；与 OInput 区别——TimePicker 有时钟图标和时间面板；与 OSelect 区别——TimePicker 面板是时间滚动列表而非下拉选项列表

---

## Part B：代码调用参考

### 导入方式

```vue
<script setup>
import { OTimePicker, OTimeRangePicker } from '@opensig/opendesign';
import dayjs from 'dayjs'; // 运行时依赖
</script>
```

### OTimePicker Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| modelValue | `string | undefined` | — | `undefined` | 1.2.4 | v-model 时间值 |
| placeholder | `string` | — | — | 1.2.4 | 占位文本 |
| inputId | `string` | — | — | 1.2.4 | 输入框 ID |
| disabled | `boolean` | — | — | 1.2.4 | 禁用 |
| readonly | `boolean` | — | — | 1.2.4 | 只读 |
| size | `SizeT` | `'large'` / `'medium'` / `'small'` | — | 1.2.4 | 尺寸 |
| round | `RoundT` | `'pill'` / CSS值 | — | 1.2.4 | 圆角 |
| color | `'normal'` / `'success'` / `'warning'` / `'danger'` | — | `'normal'` | 1.2.4 | 颜色 |
| variant | `'outline'` / `'solid'` / `'text'` | — | `'outline'` | 1.2.4 | 类型 |
| format | `string` | dayjs time format | `'HH:mm:ss'` | 1.2.4 | 时间格式 |
| clearable | `boolean` | — | — | 1.2.4 | 可清空 |
| noResponsive | `boolean` | — | — | 1.2.4 | 禁用响应式 |
| optionTitle | `string` | — | — | 1.2.4 | 浮层标题 |
| trigger | `PopupTriggerT` | — | `'click'` | 1.2.4 | 浮层触发方式 |
| popupPosition | `PopupPositionT` | `'bl'` 等 | `'bl'` | 1.2.4 | 浮层位置 |
| popupWrapper | `string | HTMLElement | null` | — | `'body'` | 1.2.4 | 浮层挂载容器 |
| unmountOnHide | `boolean` | — | `true` | 1.2.4 | 关闭时卸载 DOM |
| transition | `string` | — | — | 1.2.4 | 过渡动画 |
| hourStep | `number` | — | `1` | 1.2.4 | 小时步进 |
| minuteStep | `number` | — | `1` | 1.2.4 | 分钟步进 |
| secondStep | `number` | — | `1` | 1.2.4 | 秒步进 |
| disabledHours | `DisabledHoursFn` | — | — | 1.2.4 | 禁用小时函数 |
| disabledMinutes | `DisabledMinutesFn` | — | — | 1.2.4 | 禁用分钟函数 |
| disabledSeconds | `DisabledSecondsFn` | — | — | 1.2.4 | 禁用秒函数 |
| minTime | `string` | — | — | 1.2.4 | 最小可选时间 |
| maxTime | `string` | — | — | 1.2.4 | 最大可选时间 |

### OTimeRangePicker Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| start | `string | undefined` | — | `undefined` | 1.2.4 | v-model 开始时间 |
| end | `string | undefined` | — | `undefined` | 1.2.4 | v-model 结束时间 |
| placeholderStart | `string` | — | — | 1.2.4 | 开始时间占位文本 |
| placeholderEnd | `string` | — | — | 1.2.4 | 结束时间占位文本 |
| inputId | `string` | — | — | 1.2.4 | 输入框 ID |
| disabled | `boolean` | — | — | 1.2.4 | 禁用 |
| readonly | `boolean` | — | — | 1.2.4 | 只读 |
| size | `SizeT` | `'large'` / `'medium'` / `'small'` | — | 1.2.4 | 尺寸 |
| round | `RoundT` | `'pill'` / CSS值 | — | 1.2.4 | 圆角 |
| color | `'normal'` / `'success'` / `'warning'` / `'danger'` | — | `'normal'` | 1.2.4 | 颜色 |
| variant | `'outline'` / `'solid'` / `'text'` | — | `'outline'` | 1.2.4 | 类型 |
| format | `string` | — | `'HH:mm:ss'` | 1.2.4 | 时间格式 |
| clearable | `boolean` | — | — | 1.2.4 | 可清空 |
| noResponsive | `boolean` | — | — | 1.2.4 | 禁用响应式 |
| optionTitle | `string` | — | — | 1.2.4 | 浮层标题 |
| trigger | `PopupTriggerT` | — | `'click'` | 1.2.4 | 浮层触发方式 |
| popupPosition | `PopupPositionT` | `'bl'` 等 | `'bl'` | 1.2.4 | 浮层位置 |
| popupWrapper | `string | HTMLElement | null` | — | `'body'` | 1.2.4 | 浮层挂载容器 |
| unmountOnHide | `boolean` | — | `true` | 1.2.4 | 关闭时卸载 DOM |
| transition | `string` | — | — | 1.2.4 | 过渡动画 |
| hourStep | `number` | — | `1` | 1.2.4 | 小时步进 |
| minuteStep | `number` | — | `1` | 1.2.4 | 分钟步进 |
| secondStep | `number` | — | `1` | 1.2.4 | 秒步进 |
| disabledHours | `DisabledHoursFn` | — | — | 1.2.4 | 禁用小时函数 |
| disabledMinutes | `DisabledMinutesFn` | — | — | 1.2.4 | 禁用分钟函数 |
| disabledSeconds | `DisabledSecondsFn` | — | — | 1.2.4 | 禁用秒函数 |
| minTime | `string` | — | — | 1.2.4 | 最小可选时间 |
| maxTime | `string` | — | — | 1.2.4 | 最大可选时间 |

### Events 表

**OTimePicker 事件**：

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| change | `(newVal: string | undefined, oldVal: string | undefined)` | 1.2.4 | 值变化 |
| focus | `(evt: FocusEvent)` | 1.2.4 | 获得焦点 |
| blur | — | 1.2.4 | 失去焦点 |
| clear | `(evt?: Event)` | 1.2.4 | 清空 |
| pressEnter | — | 1.2.4 | 按下回车 |

**OTimeRangePicker 事件**：

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| change | `(newVal: TimeRangeValue, oldVal: TimeRangeValue)` | 1.2.4 | 值变化（start/end 都有值或都无值时） |
| focus | `(evt: FocusEvent)` | 1.2.4 | 任一输入框获得焦点 |
| blur | — | 1.2.4 | 两个输入框都失去焦点 |
| clear | — | 1.2.4 | 清空 |
| pressEnter | — | 1.2.4 | 按下回车（两端值合法时） |

### Slots 表

**OTimePicker 插槽**：

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| prepend | — | 始终 | InBox 前置区域 | 无 |
| append | — | 始终 | InBox 后置区域 | 无 |
| shortcut | `{ setValue, emitChange }` | 始终 | 面板快捷选项区域 | 无 |

**OTimeRangePicker 插槽**：

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| prepend | — | 始终 | InBox 前置区域 | 无 |
| append | — | 始终 | InBox 后置区域 | 无 |
| shortcut | `{ setValue(start?, end?), emitChange }` | 始终 | 面板快捷选项区域 | 无 |

### 插槽层级关系

```
InBox:
  prepend（前置区域）
  InInput / RangeInputs:
    shortcut（快捷选项，面板内）
  append（后置区域）
```

⚠️ **SSR 水合注意**：不要在 `<script setup>` 顶层用 `new Date()` 或 `Date.now()` 初始化 v-model 绑定值。服务端与客户端时间不同会导致水合不匹配。应在 `onMounted` 之后赋值：

```vue
<script setup>
import { ref, onMounted } from 'vue';
const val = ref();
onMounted(() => {
  val.value = Date.now();
});
</script>
```

### 典型使用场景与调用模板

**场景 1：基础时间选择**
适用于：选择时分秒
```vue
<script setup>
import { ref } from 'vue';
const val = ref();
</script>
<template>
  <OTimePicker v-model="val" clearable placeholder="选择时间" />
</template>
```

**场景 2：仅时分选择**
适用于：不需要秒精度
```vue
<OTimePicker v-model="val" format="HH:mm" clearable placeholder="选择时分" />
```

**场景 3：步进设置**
适用于：小时/分钟/秒按固定间隔选择
```vue
<OTimePicker v-model="val" :hour-step="2" :minute-step="15" :second-step="10" clearable />
```

**场景 4：禁用特定时间**
适用于：精确限制可选时间
```vue
<script setup>
const disabledHours = () => [0, 1, 2, 3, 4, 5, 6]; // 禁用 0-6 时
const disabledMinutes = (hour) => hour === 12 ? [0, 30] : [];
</script>
<template>
  <OTimePicker v-model="val" :disabled-hours="disabledHours" :disabled-minutes="disabledMinutes" clearable />
</template>
```

**场景 5：minTime/maxTime 约束**
适用于：快速限制可选时间范围
```vue
<OTimePicker v-model="val" min-time="09:30:00" max-time="18:30:00" clearable />
```

**场景 6：时间范围选择**
适用于：选择起止时间
```vue
<script setup>
import { ref } from 'vue';
const start = ref();
const end = ref();
</script>
<template>
  <OTimeRangePicker v-model:start="start" v-model:end="end" clearable />
</template>
```

**场景 7：范围选择 + 快捷选项**
适用于：预设时间区间快速选择
```vue
<script setup>
import { ref } from 'vue';
const start = ref();
const end = ref();
</script>
<template>
  <OTimeRangePicker v-model:start="start" v-model:end="end" clearable>
    <template #shortcut="{ setValue, emitChange }">
      <OLink @click="setValue('09:00:00', '18:00:00'); emitChange()">工作时间</OLink>
    </template>
  </OTimeRangePicker>
</template>
```

**场景 8：移动端范围选择降级**
适用于：小屏幕下使用两个独立选择器
```vue
<OFormItem label="开始">
  <OTimePicker v-model="start" :max-time="end" clearable />
</OFormItem>
<OFormItem label="结束">
  <OTimePicker v-model="end" :min-time="start" clearable />
</OFormItem>
```

**场景 9：OForm 内使用**
适用于：表单校验
```vue
<OForm :model="formData">
  <OFormItem label="时间" name="time" :rules="[{ required: true, message: '请选择时间' }]">
    <OTimePicker v-model="formData.time" clearable />
  </OFormItem>
</OForm>
```

### 常见 prop 组合速查

| 场景 | 推荐 sub-component + 组合 | 说明 |
|------|--------------------------|------|
| 选择时分秒 | OTimePicker + `v-model` + `clearable` | 最常见 |
| 仅时分 | OTimePicker + `format="HH:mm"` | 无秒列 |
| 步进选择 | OTimePicker + `hourStep` + `minuteStep` | 间隔选项 |
| 禁用特定时间 | OTimePicker + `disabledHours/Minutes/Seconds` | 精确控制 |
| 时间范围 | OTimePicker + `minTime` + `maxTime` | 快速范围约束 |
| 时间范围选择 | OTimeRangePicker + `v-model:start` + `v-model:end` | 起止时间 |
| 快捷选项 | RangePicker + `#shortcut` | setValue + emitChange |
| 移动端范围 | 两个 OTimePicker + `minTime/maxTime` | 降级方案 |

### 可覆盖的 CSS 变量

在调用处覆盖以下变量调整组件外观，**无需 `:deep` hack**：

**选择器触发器变量**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `--time-range-picker-bg-color-focus` | `var(--o-color-control2-light)` | 范围选择器分隔区域聚焦时背景色 |

**面板变量**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `--time-panel-bg` | `var(--o-color-fill2)` | 面板背景色 |
| `--time-panel-shadow` | `var(--o-shadow-2)` | 面板阴影 |
| `--time-panel-content-padding` | `6px 0` | 内容区域 padding |
| `--time-panel-footer-padding` | `8px 16px` | footer padding |
| `--time-panel-item-height` | `24px` | 时间项高度 |
| `--time-panel-item-width` | `40px` | 时间项宽度 |
| `--time-panel-item-gap` | `4px` | 时间项间距 |
| `--time-panel-col-width` | `96px` | 时间列宽度 |
| `--time-panel-col-show-item-count` | `8` | 时间列显示项数 |
| `--time-panel-col-height` | `calc(showItemCount * (itemHeight + gap))` | 时间列高度（自动计算） |
| `--time-panel-item-color` | `var(--o-color-info1)` | 普通项文字色 |
| `--time-panel-item-color-active` | `var(--o-color-primary1)` | 选中项文字色 |
| `--time-panel-item-color-disabled` | `var(--o-color-info4)` | 禁用项文字色 |
| `--time-panel-item-bg-hover` | `var(--o-color-control2-light)` | hover 背景色 |
| `--time-panel-item-bg-active` | `var(--o-color-control3-light)` | 选中背景色 |
| `--time-panel-text-size` | `var(--o-font_size-tip1)` | 面板字号 |
| `--time-panel-item-text-size` | `var(--o-font_size-tip1)` | 时间项字号 |

large 面板专属变量：

| 变量名 | large 默认值 | 说明 |
|--------|-------------|------|
| `--time-panel-item-text-size` | `var(--o-font_size-text1)` | 时间项字号增大 |

**使用示例**:
```vue
<OTimePicker v-model="val" style="--time-panel-col-width: 120px; --time-panel-col-show-item-count: 10" />
```

### 响应式行为表

| 维度 | ≤1440px (laptop) | 触控设备 | >1440px |
|------|-----------------|---------|---------|
| large 时间项字号 | tip1 | text1 | text1 |
| large 时间项行高 | tip1 | text1 | text1 |
| 时间列显示项数 | 8 | 5（touch） | 8 |
| 时间项高度 | 24px | 48px（touch） | 24px |
| 时间项间距 | 4px | 0px（touch） | 4px |
| 范围选择器 | 建议拆为两个独立选择器 | 同 | 正常范围选择器 |

### 组件布局结构

**OTimePicker**
```yaml
layout:
  component: InBox.o-time-picker.o-input
  direction: horizontal
  regions:
    - prepend(#prepend 插槽, 可选)
    - InInput(input + suffix)
      - input(时间值输入, maxlength=format.length, readonly可通过面板交互)
      - suffix(IconTime, clearable时hover显示IconClose)
      - panel(OPopup → TimePanel)
        - content: 3列横向 OScroller(时/分/秒)
          - 每列: ul > li 时间项(可选中/禁用)
          - format不含ss时秒列不显示
        - footer(确认/取消按钮)
        - shortcut(#shortcut 插槽, 可选)
    - append(#append 插槽, 可选)
```

**OTimeRangePicker**
```yaml
layout:
  component: InBox.o-time-picker.o-time-range-picker.o-input
  direction: horizontal
  regions:
    - prepend(#prepend 插槽, 可选)
    - start-InInput(开始时间输入框, readonly)
      - panel(OPopup → TimeRangePanel)
        - shortcut(#shortcut 插槽, 可选)
    - divider(span.o-time-range-picker-divider, 文字 "-")
    - end-InInput(结束时间输入框, readonly)
    - suffix(IconTime + clearable时IconClose)
    - append(#append 插槽, 可选)
  keyboard-navigation:
    Tab: start → end → 离开组件
    ArrowRight: start 末尾 → end
    ArrowLeft: end 开头 → start
```

### 设计稿识别指南

**视觉特征指纹**

1. 输入框 + 右侧时钟图标 → 匹配 OTimePicker
2. 两个输入框 + 中间 "-" 分隔 + 时钟图标 → 匹配 OTimeRangePicker
3. 弹出 3 列滚动列表（时/分/秒） → format="HH:mm:ss"
4. 弹出 2 列滚动列表（时/分） → format="HH:mm"
5. 时间列中选项间隔有规律（如 0,2,4...） → hourStep/minuteStep/secondStep
6. 面板下方有确认/取消按钮 → 所有 TimePicker 的 footer
7. 面板左侧快捷文字链接 → shortcut 插槽
8. 选中项蓝色文字 + 浅色背景 → item-color-active: primary1 + item-bg-active: control3-light

**设计 Token → Prop 值映射表**

| 设计稿属性 | 值 / 范围 | 对应 Prop | Prop 值 | 备注 |
|-----------|----------|----------|---------|------|
| 选择框边框 | 有边框 | variant | `'outline'` | 默认 |
| 选择框背景 | 实心填充 | variant | `'solid'` | — |
| 选择框无边框 | 纯文字 | variant | `'text'` | — |
| 圆角 | 全圆角 | round | `'pill'` | — |
| 尺寸 | 大/中/小 | size | `'large'`/`'medium'`/`'small'` | — |
| 禁用 | 灰色不可交互 | disabled | `true` | — |
| 清除按钮 | hover × | clearable | `true` | — |
| 格式 | HH:mm:ss | format | `'HH:mm:ss'` | 默认 |
| 格式 | HH:mm（无秒列） | format | `'HH:mm'` | — |
| 步进 | 小时 2 小时间隔 | hourStep | `2` | — |
| 步进 | 分钟 15 分钟间隔 | minuteStep | `15` | — |
| 时间范围 | 09:30 ~ 18:30 | minTime/maxTime | `'09:30:00'`/`'18:30:00'` | — |
| 红色边框 | 校验错误 | color | `'danger'` | OForm 内自动继承 |

**易混淆组件区分表**

| 本组件 | 易混淆组件 | 关键区分依据 |
|--------|-----------|-------------|
| OTimePicker | ODatePicker | TimePicker 面板是 3 列时间滚动列表，DatePicker 面板是日历网格 |
| OTimePicker | OInput | TimePicker 有时钟图标和时间弹出面板 |
| OTimePicker | OSelect | TimePicker 面板是时间滚动列表，Select 是下拉选项列表 |
| OTimeRangePicker | ODateRangePicker | TimeRange 面板是双组 3 列时间列表，DateRange 面板是日历网格 |

### 版本变更记录

| 版本 | 变更类型 | 变更内容 |
|------|---------|---------|
| 1.2.4 | 新增 | OTimePicker 与 OTimeRangePicker 组件首次发布，支持时分秒选择、步进、时间约束、键盘导航、范围选择 |
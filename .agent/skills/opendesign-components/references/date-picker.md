> ← [组件索引](../SKILL.md#组件索引) · [README](../../../README.md)

# ODatePicker 日期选择器

## Part A：设计理解卡

日期选择器组件家族包含 8 个子组件，用于日期/时间/月份/年份的单选与范围选择。所有组件继承 InBox 边框系统，使用 dayjs 进行日期格式化与计算。移动端范围选择器建议拆分为两个独立单选器 + minDate/maxDate 约束。

### 子组件一览

| 子组件 | 选择粒度 | v-model 方式 | 默认 format |
|--------|---------|-------------|------------|
| OYearPicker | 年 | `v-model="val"` | `'YYYY'` |
| OMonthPicker | 年月 | `v-model="val"` | `'YYYY/MM'` |
| ODatePicker | 年月日 | `v-model="val"` | `'YYYY/MM/DD'` |
| ODateTimePicker | 年月日时分秒 | `v-model="val"` | `'YYYY/MM/DD HH:mm:ss'` |
| OYearRangePicker | 年范围 | `v-model:start="s" v-model:end="e"` | `'YYYY'` |
| OMonthRangePicker | 年月范围 | `v-model:start="s" v-model:end="e"` | `'YYYY/MM'` |
| ODateRangePicker | 年月日范围 | `v-model:start="s" v-model:end="e"` | `'YYYY/MM/DD'` |
| ODateTimeRangePicker | 年月日时分秒范围 | `v-model:start="s" v-model:end="e"` | `'YYYY/MM/DD HH:mm:ss'` |

### 共享基础 Props（所有子组件）

**size**（属性）：尺寸。"large" 大号、"medium" 中号、"small" 小号。继承自 inputProps。

**variant**（属性）：输入框类型。"outline" 有边框轮廓、"solid" 实心填充、"text" 无边框。继承自 inputProps。

**color**（属性）：颜色。"normal" 默认、"success" 成功、"warning" 警告、"danger" 危险。OForm 内自动继承校验状态。

**round**（属性）：圆角值。"pill" 全圆角胶囊形，或 CSS border-radius 值。继承自 inputProps。

**placeholder**（属性）：占位文本。单选组件使用。继承自 inputProps。

**disabled**（属性）：禁用。继承自 inputProps。

**readonly**（属性）：只读。继承自 inputProps。

**clearable**（属性）：可清空。悬停时显示清除图标替换日历图标。

**format**（属性）：输入框显示格式。支持 dayjs format 允许的值。各组件有不同的默认值（见上表）。

**valueFormat**（属性）：绑定值格式。支持 dayjs format 值，'x' 代表时间戳。默认 'x'（毫秒时间戳）。

**defaultValue**（属性）：补全时间戳的默认值。单选为 Date 对象（默认 1970/01/01 00:00:00），范围选择器为 [Date, Date]（默认 [1970/01/01 00:00:00, 1970/12/31 23:59:59]）。

### 日期约束 Props（DatePicker/DateTimePicker）

**disabledDate**（属性）：禁用日期判断函数。接收 `{ date, year, month(0-indexed), day }`，返回 boolean。

**minDate / maxDate**（属性）：最小/最大可选日期。支持 Date/string/number 格式。

**dayStartOfWeek**（属性）：每周起始日。0=周日，1=周一（默认），...6=周六。

### 月份/年份约束 Props

**disabledMonth**（属性）：禁用月份判断函数。接收 `{ date, year, month(0-indexed) }`。MonthPicker/MonthRangePicker 使用。

**disabledYear**（属性）：禁用年份判断函数。接收 `{ date, year }`。YearPicker/MonthPicker/DatePicker 等使用。

### 时间约束 Props（DateTimePicker/DateTimeRangePicker）

继承自 OTimePicker 的时间约束属性：hourStep、minuteStep、secondStep、disabledHours、disabledMinutes、disabledSeconds、minTime、maxTime。

### 范围选择器专属 Props

**placeholderStart**（属性）：开始日期占位文本。

**placeholderEnd**（属性）：结束日期占位文本。

### 浮层控制 Props

**trigger**（属性）：浮层触发方式。"click"（默认）等 PopupTriggerT 值。

**popupPosition**（属性）：浮层位置。"bl" 左下（默认）等 PopupPositionT 值。

**popupWrapper**（属性）：浮层挂载容器。默认 "body"。

**unmountOnHide**（属性）：关闭时卸载 DOM。默认 true。

**transition**（属性）：浮层过渡动画名称。

**noResponsive**（属性）：是否禁用响应式。继承自 selectProps。

**optionTitle**（属性）：浮层标题。继承自 selectProps。

### 事件（所有单选组件）

**change**（事件）：值变化，参数 `(newVal: DateModelValue, oldVal: DateModelValue)`。

**focus**（事件）：获得焦点，参数 `(evt: FocusEvent)`。

**blur**（事件）：失去焦点。

**clear**（事件）：清空，参数 `(evt?: Event)`。

**pressEnter**（事件）：按下回车。

### 事件（范围选择器）

**change**（事件）：值变化，参数 `(start: DateModelValue, end: DateModelValue)`。

**focus**（事件）：获得焦点，参数 `(evt: FocusEvent)`。

**blur**（事件）：失去焦点（两个输入框都失去焦点时触发）。

**clear**（事件）：清空，参数 `(evt?: Event)`。

### 插槽（所有组件）

**prepend**（插槽）：前置内容，渲染在 InBox 的 prepend 区域。

**append**（插槽）：后置内容，渲染在 InBox 的 append 区域。

**shortcut**（插槽）：快捷选项。单选 Slot Props `{ setValue: (value?: number) => void, emitChange: () => void }`；范围选择 Slot Props `{ setValue: (start?: number, end?: number) => void, emitChange: () => void }`。

### 暴露方法（所有组件）

**focus(open?)**（方法）：聚焦输入框。open=true 时同时打开面板，open=false 仅聚焦。

**blur()**（方法）：失去焦点并关闭面板。

**clear()**（方法）：清除值。

**inputEl()**（方法）：获取输入框 DOM 元素（仅单选）。

### 运行时依赖

**dayjs**：日期选择器组件依赖 dayjs 作为运行时库。项目需安装 dayjs。

📱 **响应式行为**：有 media.scss 断点规则。

- **pad_v ~ laptop 区间**：large 面板 header/footer padding 缩小为 28px/40px/tip1；body padding 缩小；cell gap 缩小为 8px/12px/12px；字号 tip1。
- **触控设备**：面板标记 `.o-date-panel-touch`，面板宽度 100%，时间列显示项数缩小为 5（默认 9）。
- **范围选择器移动端降级**：建议在 pad_v 及以下使用两个独立单选器替代范围选择器，通过 minDate/maxDate 约束保证时间顺序。

🧩 **布局结构**：单选组件根元素为 InBox（继承边框/圆角/颜色/尺寸），内部为 InnerDatePicker（InInput + 日历图标 + OPopup 面板）。范围选择器根元素为 InBox，内部为两个 InInput（start + end）+ 中间分隔线 "-" + 日历图标/清除按钮。面板由 DatePanel/TimePanel 等内部组件渲染，包含 header（年份/月份切换按钮）、body（日期/月份/年份网格）、footer（确认/取消按钮）、shortcut 区域（可选）。
```yaml
# 简化结构摘要
direction(单选): InBox水平排列 [InnerDatePicker(input+icon+popup)]
direction(范围): InBox水平排列 [start-InInput | divider(-) | end-InInput | suffix-icon(calendar/clear)]
note: 面板内部包含 header(年份月份切换) + body(网格) + footer(确认取消) + shortcut(快捷选项,可选)
```

🔍 **设计稿识别指南**：
- **视觉特征指纹**：类似 Input 的输入框 + 右侧日历图标 + 点击后弹出日历网格面板
- **面板网格类型**：7列日网格（含星期头）= date/datetime 模式；4列月网格 = month 模式；4列年网格 = year 模式
- **范围选择器**：两个输入框 + 中间横线分隔 + 日历图标 → 匹配 RangePicker 系列
- **时间面板**：日历网格下方有 3 列滚动列表（时/分/秒） → 匹配 DateTimePicker
- **Token → Prop 映射**：日历图标在输入框右侧=所有 DatePicker 系列组件固定; 有边框=variant:outline; 实心背景=variant:solid; 胶囊圆角=round:pill; 大号=size:large; 禁用=disabled:true; 清除按钮=clearable:true; 显示格式=format:YYYY/MM/DD 等; 红色边框=color:danger（OForm 内自动继承）
- **易混淆组件区分**：与 OInput 区别——DatePicker 有日历图标和弹出面板；与 OTimePicker 区别——DatePicker 面板包含日期网格，TimePicker 只有时间滚动列表；与 OCascaderV2 区别——DatePicker 面板是日历网格，Cascader 是多列级联菜单

---

## Part B：代码调用参考

### 导入方式

```vue
<script setup>
import {
  ODatePicker,
  ODateTimePicker,
  OMonthPicker,
  OYearPicker,
  ODateRangePicker,
  ODateTimeRangePicker,
  OMonthRangePicker,
  OYearRangePicker,
} from '@opensig/opendesign';
import dayjs from 'dayjs'; // 运行时依赖
</script>
```

### 共享 Props 表（所有子组件通用）

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| placeholder | `string` | — | — | 1.2.4 | 占位文本 |
| inputId | `string` | — | — | 1.2.4 | 输入框 ID |
| disabled | `boolean` | — | — | 1.2.4 | 禁用 |
| readonly | `boolean` | — | — | 1.2.4 | 只读 |
| size | `SizeT` | `'large'` / `'medium'` / `'small'` | — | 1.2.4 | 尺寸 |
| round | `RoundT` | `'pill'` / CSS值 | — | 1.2.4 | 圆角 |
| color | `'normal'` / `'success'` / `'warning'` / `'danger'` | — | `'normal'` | 1.2.4 | 颜色 |
| variant | `'outline'` / `'solid'` / `'text'` | — | `'outline'` | 1.2.4 | 类型 |
| format | `string` | dayjs format | 各组件不同 | 1.2.4 | 显示格式 |
| valueFormat | `string` | dayjs format / `'x'` | `'x'` | 1.2.4 | 绑定值格式 |
| clearable | `boolean` | — | — | 1.2.4 | 可清空 |
| noResponsive | `boolean` | — | — | 1.2.4 | 禁用响应式 |
| optionTitle | `string` | — | — | 1.2.4 | 浮层标题 |
| trigger | `PopupTriggerT` | — | `'click'` | 1.2.4 | 浮层触发方式 |
| popupPosition | `PopupPositionT` | `'bl'` 等 | `'bl'` | 1.2.4 | 浮层位置 |
| popupWrapper | `string | HTMLElement | null` | — | `'body'` | 1.2.4 | 浮层挂载容器 |
| unmountOnHide | `boolean` | — | `true` | 1.2.4 | 关闭时卸载 DOM |
| transition | `string` | — | — | 1.2.4 | 过渡动画 |
| defaultValue | `Date` (单选) / `Date[]` (范围) | — | `1970/01/01 00:00:00` (单选) / `[1970/01/01, 1970/12/31]` (范围) | 1.2.4 | 补全时间戳 |

### 约束 Props 表（按适用组件标注）

| 参数名 | 类型 | 适用组件 | 默认值 | 引入版本 | 说明 |
|--------|------|---------|--------|---------|------|
| disabledDate | `DisabledDateFn` | DatePicker, DateTimePicker, DateRangePicker, DateTimeRangePicker | — | 1.2.4 | 禁用日期判断 |
| disabledMonth | `DisabledMonthFn` | MonthPicker, MonthRangePicker | — | 1.2.4 | 禁用月份判断 |
| disabledYear | `DisabledYearFn` | YearPicker, MonthPicker, DatePicker 等 | — | 1.2.4 | 禁用年份判断 |
| minDate | `DateModelValue` | DatePicker, DateTimePicker, DateRangePicker 等 | — | 1.2.4 | 最小可选日期 |
| maxDate | `DateModelValue` | DatePicker, DateTimePicker, DateRangePicker 等 | — | 1.2.4 | 最大可选日期 |
| dayStartOfWeek | `number` (0-6) | DatePicker, DateTimePicker 等 | `1` | 1.2.4 | 每周起始日（1=周一） |
| hourStep | `number` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 小时步进 |
| minuteStep | `number` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 分钟步进 |
| secondStep | `number` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 秒步进 |
| disabledHours | `DisabledHoursFn` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 禁用小时 |
| disabledMinutes | `DisabledMinutesFn` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 禁用分钟 |
| disabledSeconds | `DisabledSecondsFn` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 禁用秒 |
| minTime | `string` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 最小可选时间 |
| maxTime | `string` | DateTimePicker, DateTimeRangePicker | — | 1.2.4 | 最大可选时间 |

### 范围选择器专属 Props 表

| 参数名 | 类型 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|---------|------|
| placeholderStart | `string` | — | 1.2.4 | 开始日期占位文本 |
| placeholderEnd | `string` | — | 1.2.4 | 结束日期占位文本 |

### 各组件 format 默认值对照

| 子组件 | format 默认值 | 说明 |
|--------|-------------|------|
| OYearPicker | `'YYYY'` | 仅年份 |
| OMonthPicker | `'YYYY/MM'` | 年月 |
| ODatePicker | `'YYYY/MM/DD'` | 年月日 |
| ODateTimePicker | `'YYYY/MM/DD HH:mm:ss'` | 年月日时分秒 |
| OYearRangePicker | `'YYYY'` | 仅年份 |
| OMonthRangePicker | `'YYYY/MM'` | 年月 |
| ODateRangePicker | `'YYYY/MM/DD'` | 年月日 |
| ODateTimeRangePicker | `'YYYY/MM/DD HH:mm:ss'` | 年月日时分秒 |

### Events 表

**单选组件通用事件**：

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| change | `(newVal: DateModelValue, oldVal: DateModelValue)` | 1.2.4 | 值变化 |
| focus | `(evt: FocusEvent)` | 1.2.4 | 获得焦点 |
| blur | — | 1.2.4 | 失去焦点 |
| clear | `(evt?: Event)` | 1.2.4 | 清空 |
| pressEnter | — | 1.2.4 | 按下回车 |

**范围选择器事件**：

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| change | `(start: DateModelValue, end: DateModelValue)` | 1.2.4 | 值变化 |
| focus | `(evt: FocusEvent)` | 1.2.4 | 任一输入框获得焦点 |
| blur | — | 1.2.4 | 两个输入框都失去焦点 |
| clear | `(evt?: Event)` | 1.2.4 | 清空 |

### Slots 表

**单选组件插槽**：

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| prepend | — | 始终 | InBox 前置区域 | 无 |
| append | — | 始终 | InBox 后置区域 | 无 |
| shortcut | `{ setValue, emitChange }` | 始终 | 快捷选项区域 | 无 |

**范围选择器插槽**：

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| prepend | — | 始终 | InBox 前置区域 | 无 |
| append | — | 始终 | InBox 后置区域 | 无 |
| shortcut | `{ setValue(start?, end?), emitChange }` | 始终 | 快捷选项区域 | 无 |

### 插槽层级关系

```
InBox:
  prepend（前置区域）
  InnerDatePicker / RangeInputs:
    shortcut（快捷选项区域，面板内）
  append（后置区域）
```

⚠️ **SSR 水合注意**：不要在 `<script setup>` 顶层用 `new Date()` 或 `Date.now()` 初始化 v-model 绑定值（如 `const val = ref(Date.now())`）。服务端与客户端时间不同会导致水合不匹配。应在 `onMounted` 之后赋值：

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

**场景 1：日期选择**
适用于：选择年月日
```vue
<script setup>
import { ref } from 'vue';
const val = ref();
</script>
<template>
  <ODatePicker v-model="val" clearable placeholder="选择日期" />
</template>
```

**场景 2：日期时间选择**
适用于：选择年月日时分秒
```vue
<script setup>
import { ref } from 'vue';
const val = ref();
</script>
<template>
  <ODateTimePicker v-model="val" clearable placeholder="选择日期时间" />
</template>
```

**场景 3：月份选择**
适用于：选择年月
```vue
<OMonthPicker v-model="val" clearable placeholder="选择月份" />
```

**场景 4：年份选择**
适用于：选择年份
```vue
<OYearPicker v-model="val" clearable placeholder="选择年份" />
```

**场景 5：日期范围选择**
适用于：选择起止日期
```vue
<script setup>
import { ref } from 'vue';
const start = ref();
const end = ref();
</script>
<template>
  <ODateRangePicker v-model:start="start" v-model:end="end" clearable />
</template>
```

**场景 6：范围选择 + 快捷选项**
适用于：预设时间区间快速选择
```vue
<script setup>
import { ref } from 'vue';
import dayjs from 'dayjs';
const start = ref();
const end = ref();
</script>
<template>
  <ODateRangePicker v-model:start="start" v-model:end="end" clearable>
    <template #shortcut="{ setValue, emitChange }">
      <OLink @click="setValue(dayjs().startOf('day').valueOf(), dayjs().endOf('day').valueOf()); emitChange()">今天</OLink>
      <OLink @click="setValue(dayjs().subtract(6, 'day').startOf('day').valueOf(), dayjs().endOf('day').valueOf()); emitChange()">最近7天</OLink>
    </template>
  </ODateRangePicker>
</template>
```

**场景 7：禁用特定日期**
适用于：限制可选日期范围
```vue
<script setup>
const disabledDate = ({ date, day }) => day === 0 || day === 6; // 禁用周六周日
const disabledDateFuture = ({ date }) => date > new Date(); // 禁用未来日期
</script>
<template>
  <ODatePicker v-model="val" :disabled-date="disabledDateFuture" clearable />
</template>
```

**场景 8：自定义格式**
适用于：需要特定日期格式
```vue
<ODatePicker v-model="val" format="YYYY-MM-DD" value-format="YYYY-MM-DD" clearable />
<ODateTimePicker v-model="val" format="YYYY年MM月DD日 HH时mm分" clearable />
```

**场景 9：时间约束**
适用于：DateTimePicker 限制时间选择
```vue
<script setup>
const disabledHours = () => [0, 1, 2, 3, 4, 5]; // 禁用 0-5 时
const disabledMinutes = (hour) => hour === 12 ? [0, 30] : []; // 12时禁用 0分和30分
</script>
<template>
  <ODateTimePicker v-model="val" :disabled-hours="disabledHours" :disabled-minutes="disabledMinutes" min-time="06:00:00" max-time="23:59:59" clearable />
</template>
```

**场景 10：移动端范围选择降级**
适用于：小屏幕下使用两个独立选择器
```vue
<script setup>
import { ref } from 'vue';
const start = ref();
const end = ref();
</script>
<template>
  <OFormItem label="开始">
    <ODatePicker v-model="start" :max-date="end" clearable />
  </OFormItem>
  <OFormItem label="结束">
    <ODatePicker v-model="end" :min-date="start" clearable />
  </OFormItem>
</template>
```

**场景 11：OForm 内使用**
适用于：表单校验
```vue
<OForm :model="formData">
  <OFormItem label="日期" name="date" :rules="[{ required: true, message: '请选择日期' }]">
    <ODatePicker v-model="formData.date" clearable />
  </OFormItem>
</OForm>
```

### 常见 prop 组合速查

| 场景 | 推荐 sub-component + 组合 | 说明 |
|------|--------------------------|------|
| 选择日期 | ODatePicker + `v-model` + `clearable` | 最常见 |
| 选择日期时间 | ODateTimePicker + `v-model` + `clearable` | 含时分秒 |
| 选择月份 | OMonthPicker + `v-model` + `clearable` | — |
| 选择年份 | OYearPicker + `v-model` + `clearable` | — |
| 日期范围 | ODateRangePicker + `v-model:start` + `v-model:end` | — |
| 日期时间范围 | ODateTimeRangePicker + `v-model:start` + `v-model:end` | — |
| 禁用日期 | ODatePicker + `:disabled-date` 或 `minDate` + `maxDate` | — |
| 快捷选项 | RangePicker + `#shortcut` 插槽 | setValue + emitChange |
| 移动端范围 | 两个 ODatePicker + `:min-date` / `:max-date` | 降级方案 |

### 可覆盖的 CSS 变量

在调用处覆盖以下变量调整组件外观，**无需 `:deep` hack**：

**选择器触发器变量**（继承 InBox/OInput 变量）：

| 变量名 | 说明 |
|--------|------|
| `--date-range-picker-bg-color-focus` | 范围选择器中间分隔区域聚焦时的背景色，默认 `var(--o-color-control2-light)` |

**面板变量**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `--date-panel-bg` | `var(--o-color-fill2)` | 面板背景色 |
| `--date-panel-shadow` | `var(--o-shadow-2)` | 面板阴影 |
| `--date-panel-operation-padding-x` | `28px` | header/footer 横向 padding |
| `--date-panel-operation-height` | `40px` | header/footer 高度 |
| `--date-panel-operation-text-size` | `var(--o-font_size-tip1)` | header/footer 字号 |
| `--date-panel-text-size` | `var(--o-font_size-tip1)` | 日期网格字号 |
| `--date-panel-body-padding-date` | `16px 16px 8px 16px` | 日期 body padding |
| `--date-panel-body-padding-month` | `12px 28px` | 月份 body padding |
| `--date-panel-body-padding-year` | `12px 32px` | 年份 body padding |
| `--date-panel-cell-gap-date-y` | `8px` | 日期行间距 |
| `--date-panel-cell-gap-month-x` | `32px` | 月份列间距 |
| `--date-panel-cell-gap-year-x` | `40px` | 年份列间距 |
| `--date-panel-cell-width-date` | `40px` | 日期单元格宽度 |
| `--date-panel-cell-width-month` | `64px` | 月份单元格宽度 |
| `--date-panel-cell-width-year` | `56px` | 年份单元格宽度 |
| `--date-panel-cell-color` | `var(--o-color-info1)` | 普通日期文字色 |
| `--date-panel-cell-color-active` | `var(--o-color-info1-inverse)` | 选中日期文字反色 |
| `--date-panel-cell-color-disabled` | `var(--o-color-info4)` | 禁用日期文字色 |
| `--date-panel-cell-bg-hover` | `var(--o-color-control2-light)` | hover 背景色 |
| `--date-panel-cell-bg-active` | `var(--o-color-primary1)` | 选中背景色 |
| `--date-panel-cell-bg-range` | `var(--o-color-control2-light)` | 范围中间日期背景色 |
| `--date-panel-cell-today-bd-color` | `var(--o-color-primary1)` | 今日日期边框色 |
| `--date-panel-shortcut-text-size` | `var(--o-font_size-tip1)` | 快捷选项字号 |

**使用示例**:
```vue
<ODatePicker v-model="val" style="--date-panel-cell-bg-active: #1a73e8" />
```

### 响应式行为表

| 维度 | pad_v ~ laptop | 触控设备 | > laptop |
|------|---------------|---------|---------|
| large 面板 header padding | 28px | 28px | 24px |
| large 面板 header 高度 | 40px | 40px | 48px |
| large 面板字号 | tip1 | tip1 | text1 |
| large 日期行间距 | 8px | 8px | 12px |
| 时间列显示项数 | 9 | 5（touch） | 9 |
| 范围选择器 | 建议拆为两个独立选择器 | 建议拆为两个 | 正常范围选择器 |

### 组件布局结构

**单选选择器**
```yaml
layout:
  component: InBox.o-date-picker.o-input
  direction: horizontal
  regions:
    - prepend(#prepend 插槽, 可选)
    - InnerDatePicker(InInput + 日历图标 + OPopup 面板)
      - input(readonly, 显示 format 格式化值)
      - icon(IconCalendar, has-icon=true)
      - panel(OPopup)
        - InnerPanel(DatePanel/TimePanel)
          - header(年份月份切换按钮)
          - body(日期/月份/年份网格)
          - footer(确认/取消按钮, datetime模式)
          - shortcut(#shortcut 插槽, 可选)
    - append(#append 插槽, 可选)
```

**范围选择器**
```yaml
layout:
  component: InBox.o-date-range-picker.o-input
  direction: horizontal
  regions:
    - prepend(#prepend 插槽, 可选)
    - start-InInput(开始日期输入框, readonly)
      - panel(DateRangePanel)
        - shortcut(#shortcut 插槽, 可选)
    - divider(span.o-date-range-picker-divider, 文字 "-")
    - end-InInput(结束日期输入框, readonly)
    - suffix-icon(IconCalendar / IconClose(clearable时hover))
    - append(#append 插槽, 可选)
```

### 设计稿识别指南

**视觉特征指纹**

1. 输入框 + 右侧日历图标 → 匹配 DatePicker 系列
2. 两个输入框 + 中间 "-" 分隔 + 日历图标 → 匹配 RangePicker 系列
3. 日历网格面板（7列含星期头） → date/datetime 模式
4. 4列月网格面板 → month 模式
5. 4列年网格面板 → year 模式
6. 日历网格 + 下方 3 列时间滚动列表 → datetime 模式
7. 面板左侧快捷选项文字链接 → shortcut 插槽
8. 选中日期蓝色背景 + 反色文字 → date-panel-cell-bg-active: primary1
9. 范围中间日期浅色背景 → date-panel-cell-bg-range: control2-light
10. 今日日期边框色 → date-panel-cell-today-bd-color: primary1

**设计 Token → Prop 值映射表**

| 设计稿属性 | 值 / 范围 | 对应 Prop | Prop 值 | 备注 |
|-----------|----------|----------|---------|------|
| 选择框边框 | 有边框 | variant | `'outline'` | 默认 |
| 选择框背景 | 实心填充 | variant | `'solid'` | — |
| 选择框无边框 | 纯文字 | variant | `'text'` | — |
| 圆角 | 全圆角 | round | `'pill'` | — |
| 尺寸 | 大/中/小 | size | `'large'`/`'medium'`/`'small'` | — |
| 禁用 | 灰色不可交互 | disabled | `true` | — |
| 清除按钮 | hover 显示 × | clearable | `true` | — |
| 显示格式 | YYYY/MM/DD | format | `'YYYY/MM/DD'` | DatePicker 默认 |
| 显示格式 | YYYY/MM/DD HH:mm:ss | format | `'YYYY/MM/DD HH:mm:ss'` | DateTimePicker 默认 |
| 禁用日期 | 部分灰色 | disabledDate | 函数 | — |
| 周起始日 | 周一开始 | dayStartOfWeek | `1` | 默认 |
| 快捷选项 | 面板左侧文字链接 | #shortcut | 插槽 | setValue + emitChange |
| 红色边框 | 校验错误 | color | `'danger'` | OForm 内自动继承 |

**易混淆组件区分表**

| 本组件 | 易混淆组件 | 关键区分依据 |
|--------|-----------|-------------|
| ODatePicker | OInput | DatePicker 有日历图标和弹出面板，Input 是纯输入框 |
| ODatePicker | OTimePicker | DatePicker 面板包含日期网格，TimePicker 只有时间滚动列 |
| ODateTimePicker | ODatePicker | DateTimePicker 面板在日期网格下方有时间选择区域 |
| ODateRangePicker | ODatePicker | RangePicker 是两个输入框 + "-" 分隔，DatePicker 是单个输入框 |
| ODatePicker | OCascaderV2 | DatePicker 面板是日历网格，Cascader 是多列级联菜单 |

### 版本变更记录

| 版本 | 变更类型 | 变更内容 |
|------|---------|---------|
| 1.2.4 | 新增 | 8 个日期选择器子组件首次发布：ODatePicker/ODateTimePicker/OMonthPicker/OYearPicker + 4 个 RangePicker，依赖 dayjs 运行时 |
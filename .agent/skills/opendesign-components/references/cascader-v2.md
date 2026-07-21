> ← [组件索引](../SKILL.md#组件索引) · [README](../../../README.md)

# OCascaderV2 级联选择器（V2）

## Part A：设计理解卡

OCascaderV2 是级联选择器的 PC 重构版本（与原 OCascader 完全独立），支持单选/多选、可搜索、懒加载、选择前拦截、路径值模式、任意层级选中、多级面板横向排列等完整功能。由 OCascaderV2（选择器触发器）+ OCascaderV2Panel（下拉面板）+ OCascaderV2Label（选项行渲染）三组件协作。

### 选择器触发器外观

**size**（属性）：选择框尺寸。"large" 大号（默认）、"medium" 中号。不支持 small。

**variant**（属性）：选择框类型。"outline" 有边框轮廓（默认）、"solid" 实心填充、"text" 无边框。

**color**（属性）：选择框颜色。"normal" 默认、"success" 成功、"warning" 警告、"danger" 危险。OForm 内自动继承校验状态。默认 normal。

**round**（属性）：圆角值。"pill" 全圆角胶囊形，或自定义 CSS 值。

**clearable**（属性）：可一键清空。开启后悬停时显示清除图标（IconClose）替换下拉箭头。默认继承 select 的 clearable 配置。

**disabled**（属性）：整体禁用，不可交互。默认继承 select 的 disabled 配置。

**loading**（属性）：加载中状态，显示旋转加载图标，不可交互。默认继承 select 的 loading 配置。

**placeholder**（属性）：选择框提示文本。默认继承 select 的 placeholder 配置。

### 选项数据与值模式

**options**（属性）：级联选项树数据，每项 `{ value: string|number, label?: string, children?: Array<CascaderV2OptionT>, disabled?: boolean, leaf?: boolean }`。value 必填，children 存在时可展开下一级。

**modelValue**（属性/v-model）：选中值。形态由 emitPath + multiple 组合决定：
- 单选 + emitPath=false → 叶子 value（string|number）
- 单选 + emitPath=true → 从根到叶子的路径数组
- 多选 + emitPath=false → 叶子 value 数组
- 多选 + emitPath=true → 路径数组 的数组

**emitPath**（属性）：选中值是否返回路径数组。true 时 change/update:modelValue 返回完整路径，false 时只返回叶子值。默认 true。

**pathMode**（属性）：Panel 内部事件派发时是否使用路径模式。与 emitPath 对应，用于 OCascaderV2Panel 独立使用场景。默认 false。

**showAllLevels**（属性）：输入框中是否显示完整路径（如"浙江省 / 杭州 / 西湖"）。true 显示全路径，false 只显示当前层级 label。默认 true。

### 展开与交互

**expandTrigger**（属性）：次级菜单展开触发方式。"click" 点击展开（默认）、"hover" 鼠标悬停展开。触控设备强制降级为 click。

**allowSelectAnyNode**（属性）：是否允许选中任意层级节点。false（默认）时仅叶子节点可选中，父节点显示半选/全选汇总态；true 时任意节点可独立选中。单选模式下 allowSelectAnyNode=true 时使用 ORadio 渲染，false 时无 Radio/Checkbox。

**multiple**（属性）：多选模式。开启后选项使用 OCheckbox 渲染，选中值以 tag 展示在输入框内。默认继承 select 的 multiple 配置（false）。

**filterable**（属性）：可搜索。开启后输入框变为可编辑输入，输入关键词自动筛选匹配的叶子节点（allowSelectAnyNode=true 时搜索所有层级）。关键词高亮显示（primary 色 + font-weight:600）。默认关闭。

**beforeSelect**（属性）：选择前拦截回调。接收 `(value, currentValue)` 返回 true/false/string|number/Promise。true 放行、false 阻止、返回新值改写选中项、Promise 支持异步确认。

### 多选标签

**maxTagCount**（属性）：多选标签最大显示数量。超出部分折叠为 +N。默认不限制。

**foldLabel**（属性）：自定义折叠文本。接收折叠的 tag 数组，返回字符串。默认显示 `+N`。

**showFoldTags**（属性）：折叠 tag 的展开方式。true/hover（默认）悬停展开、click 点击展开、false 不展开。折叠 tag 通过 OPopover 浮层展示。

### 懒加载

**lazy**（属性）：是否启用懒加载。开启后 options 最初可为空/仅根级，通过 lazyload 动态加载子节点。默认 false。

**lazyload**（属性）：懒加载回调。接收 `(node, resolve, reject)` 或返回 Promise。node 包含 `{ value, level, isLeaf, data, path, label }`（根节点 value 为 null）。resolve 传入子节点数组，reject 失败回调。

### 浮层控制

**trigger**（属性）：选项浮层触发方式。"click-outclick"（默认）点击打开外部点击关闭、支持 OPopup 所有 trigger 值。

**optionPosition**（属性）：浮层位置。"bl" 左下（默认）、"tl"/"tr"/"bottom"/"br"/"left"/"right" 等所有 PopupPositionT 值。

**optionWidthMode**（属性）：浮层宽度模式。"auto" 自适应（默认）、"min-width" 最小宽度与选择框一致、"width" 宽度与选择框一致。

**unmountOnHide**（属性）：关闭浮层时卸载所有选项 DOM。默认 true。

**optionsWrapper**（属性）：浮层挂载容器。默认 "body"，可传 HTMLElement 或 null。

**transition**（属性）：浮层过渡动画名称。

**beforeOptionsShow**（属性）：浮层显示前回调，返回 false 阻止显示。

**beforeOptionsHide**（属性）：浮层隐藏前回调，返回 false 阻止隐藏。filterable 模式下点击 InBox 内部自动阻止关闭。

### 事件

**update:modelValue**（事件）：v-model 值更新，形态随 emitPath/multiple 变化。

**change**（事件）：选中值变化，参数与 update:modelValue 一致。

**options-visible-change**（事件）：浮层显示/隐藏切换，参数 boolean。

**clear**（事件）：清空按钮点击，参数原始 DOM Event。

**lazyload-error**（事件）：懒加载失败，参数 CascaderV2LazyNodeT 节点信息。

### 插槽

**default**（OCascaderV2 插槽）：自定义整个下拉面板内容，替换 OCascaderV2Panel。

**tagFold**（OCascaderV2 插槽）：自定义折叠 tag 文本，替换默认 `+N`。

**arrow**（OCascaderV2 插槽）：自定义下拉箭头图标，Slot Props `{ active: boolean }` 表示面板是否展开。

**suffix**（OCascaderV2 插槽）：自定义后缀区域，Slot Props `{ active: boolean }`。

### Panel 独立使用

OCascaderV2Panel 可独立使用（不依赖浮层触发），用于面板直接嵌入页面的场景。Props 与 OCascaderV2 部分重叠：modelValue、options、pathMode、expandTrigger、size、showAllLevels、filterable、lazy、lazyload。通过 cascaderV2InjectKey 注入与父级通信。

📱 **响应式行为**：有 media.scss 断点规则。

- **pad_v ~ laptop 区间**：large 选择框高度缩小为 36px、图标缩小为 control-s、字号 tip1；large 面板选项 padding 缩小为 6px 12px、字号 tip1、图标缩小为 s；medium 选择框高度缩小为 28px、图标 control-xs、字号 tip1；medium 面板选项 padding 缩小为 2px 12px、字号 tip1、图标 xs。
- 触控设备 expandTrigger 强制降级为 click。

🧩 **布局结构**：OCascaderV2 根元素为 InBox（继承 InBox 的边框/圆角/颜色/尺寸系统），内含 OScroller 包裹的值展示区域（单选为 input、多选为 tag 列表 + input）+ 后缀图标区域（clear/loading/arrow）。浮层通过 OPopup 定位，内部 OCascaderV2Panel 为多列水平排列，每列由 OScroller + ul.o-cascader-v2-options 组成，列间有 ODivider(direction=v) 分隔。filterable 模式下面板切换为搜索结果列表。
```yaml
# 简化结构摘要
direction: OCascaderV2 为水平inline-flex(InBox); Panel 为多列横向flex+分隔线
regions(OCascaderV2): [value-list(值展示/input/tags), suffix-icon(clear/loading/arrow)]
regions(Panel): [column*1~N(各级菜单列, OScroller+ul+li+OCascaderV2Label), divider(v分隔线*0~N-1)]
note: 筛选模式下面板变为单列搜索结果列表；OCascaderV2Label 内含 ORadio/OCheckbox(多选/allowSelectAnyNode) + 文本 + 展开箭头
```

🔍 **设计稿识别指南**：
- **视觉特征指纹**：类似 Select 的选择框 + 下拉后展示多列横向排列的级联菜单（列间有竖分隔线）+ 每列选项左侧有 Checkbox/Radio + 右侧非叶子节点有箭头
- **多列级联面板**：多列列表横向排列，列间有竖线分隔 → 匹配 OCascaderV2（而非 OCascader 旧版的树形展开）
- **搜索模式面板**：单列搜索结果列表 + 关键词蓝色高亮 → 匹配 OCascaderV2（filterable=true）
- **Token → Prop 映射**：选择框有边框=variant:outline；选择框实心背景=variant:solid；选择框无边框=variant:text；胶囊圆角=round:pill；选项有 Checkbox=multiple:true；选项有 Radio（单选+任意节点）=allowSelectAnyNode:true；输入框可输入搜索=filterable:true；hover 展开子级=expandTrigger:hover；输入框显示全路径=showAllLevels:true；加载中旋转图标=loading:true
- **易混淆组件区分**：与 OCascader 区别——V2 是 PC 重构版，面板为多列横向排列而非旧版的树形展开；与 OSelect 区别——Cascader 是级联多级选择，Select 是单级选择

---

## Part B：代码调用参考

### 导入方式

```vue
<script setup>
import { OCascaderV2, OCascaderV2Panel } from '@opensig/opendesign';
</script>
```

### OCascaderV2 Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| modelValue | `CascaderV2ValueT` | — | — | 1.2.4 | v-model 选中值（形态随 emitPath/multiple 变化） |
| options | `Array<CascaderV2OptionT>` | — | — | 1.2.4 | 级联选项树 |
| size | `'large' | 'medium'` | — | `'large'` | 1.2.4 | 选择框尺寸 |
| round | `RoundT` | `'pill'` / CSS值 | — | 1.2.4 | 圆角 |
| color | `'normal' | 'success' | 'warning' | 'danger'` | — | `'normal'` | 1.2.4 | 颜色（OForm 内自动继承） |
| variant | `'outline' | 'solid' | 'text'` | — | `'outline'` | 1.2.4 | 选择框类型 |
| disabled | `boolean` | — | — | 1.2.4 | 禁用 |
| loading | `boolean` | — | — | 1.2.4 | 加载中 |
| clearable | `boolean` | — | — | 1.2.4 | 可清空 |
| multiple | `boolean` | — | — | 1.2.4 | 多选 |
| placeholder | `string` | — | — | 1.2.4 | 提示文本 |
| filterable | `boolean` | — | `false` | 1.2.4 | 可搜索 |
| maxTagCount | `number` | — | — | 1.2.4 | 多选标签最大数量 |
| foldLabel | `(tags: Array<SelectOptionT>) => string` | — | — | 1.2.4 | 自定义折叠文案 |
| showFoldTags | `boolean | 'hover' | 'click'` | — | `'hover'` | 1.2.4 | 折叠 tag 展开方式 |
| beforeSelect | `CascaderV2BeforeSelectFn` | — | — | 1.2.4 | 选择前拦截回调 |
| transition | `string` | — | — | 1.2.4 | 浮层过渡动画 |
| unmountOnHide | `boolean` | — | `true` | 1.2.4 | 关闭时卸载选项 DOM |
| optionPosition | `PopupPositionT` | `'bl'`/`'tl'`/`'tr'`/`'bottom'`/`'br'` 等 | `'bl'` | 1.2.4 | 浮层位置 |
| optionsWrapper | `string | HTMLElement | null` | — | `'body'` | 1.2.4 | 浮层挂载容器 |
| trigger | `PopupTriggerT` | `'click-outclick'` 等 | `'click-outclick'` | 1.2.4 | 浮层触发方式 |
| optionWidthMode | `'auto' | 'min-width' | 'width'` | — | `'auto'` | 1.2.4 | 浮层宽度模式 |
| beforeOptionsShow | `() => Promise<boolean> | boolean` | — | — | 1.2.4 | 浮层显示前回调 |
| beforeOptionsHide | `() => Promise<boolean> | boolean` | — | — | 1.2.4 | 浮层隐藏前回调 |
| pathMode | `boolean` | — | `false` | 1.2.4 | Panel 内部路径模式 |
| expandTrigger | `'click' | 'hover'` | — | `'click'` | 1.2.4 | 展开触发方式 |
| showAllLevels | `boolean` | — | `true` | 1.2.4 | 输入框显示完整路径 |
| emitPath | `boolean` | — | `true` | 1.2.4 | 选中值返回路径数组 |
| allowSelectAnyNode | `boolean` | — | `false` | 1.2.4 | 任意层级可选中 |
| lazy | `boolean` | — | `false` | 1.2.4 | 懒加载模式 |
| lazyload | `CascaderV2LazyloadFn` | — | — | 1.2.4 | 懒加载回调 |

### OCascaderV2Panel Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| modelValue | `CascaderV2ValueT` | — | `''` | 1.2.4 | 选中值 |
| options | `Array<CascaderV2OptionT>` | — | — | 1.2.4 | 级联选项树 |
| pathMode | `boolean` | — | `false` | 1.2.4 | 路径模式 |
| expandTrigger | `'click' | 'hover'` | — | `'click'` | 1.2.4 | 展开触发方式 |
| size | `'large' | 'medium'` | — | `'large'` | 1.2.4 | 面板尺寸 |
| showAllLevels | `boolean` | — | `true` | 1.2.4 | 显示完整路径 |
| filterable | `boolean` | — | — | 1.2.4 | 可搜索 |
| lazy | `boolean` | — | `false` | 1.2.4 | 懒加载 |
| lazyload | `CascaderV2LazyloadFn` | — | — | 1.2.4 | 懒加载回调 |

### Events 表（OCascaderV2）

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| update:modelValue | `CascaderV2NodeValueT | CascaderV2NodePathT | Array<...> | undefined` | 1.2.4 | v-model 值更新 |
| change | 同 update:modelValue | 1.2.4 | 选中值变化 |
| options-visible-change | `(visible: boolean)` | 1.2.4 | 浮层显示/隐藏 |
| clear | `(evt: Event)` | 1.2.4 | 清空按钮点击 |
| lazyload-error | `(node: CascaderV2LazyNodeT)` | 1.2.4 | 懒加载失败 |

### Slots 表（OCascaderV2）

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| default | — | 始终 | 整个下拉面板 | OCascaderV2Panel |
| tagFold | — | 多选折叠 tag 时 | 折叠 tag 文本 | `+N` |
| arrow | `{ active: boolean }` | 始终 | 下拉箭头图标 | IconChevronDown（active 时旋转180°） |
| suffix | `{ active: boolean }` | 始终 | 后缀区域 | 无 |

### 插槽层级关系

```
OCascaderV2:
  default（整个下拉面板，替换 OCascaderV2Panel）
  tagFold（折叠 tag 文本，多选折叠时）
  arrow（下拉箭头图标）
  suffix（后缀区域）

OCascaderV2Panel 内部不暴露外部插槽。
OCascaderV2Label 内部使用 OCheckbox/ORadio + OPopover(文本溢出提示)，均为内部组件。
```

### 典型使用场景与调用模板

**场景 1：基础单选**
适用于：省市区三级联动等
```vue
<script setup>
import { ref } from 'vue';
const val = ref();
const options = [
  { label: '浙江', value: 'zj', children: [
    { label: '杭州', value: 'hz', children: [
      { label: '西湖', value: 'xh' },
    ] },
  ] },
  { label: '江苏', value: 'js', children: [
    { label: '南京', value: 'nj' },
  ] },
];
</script>
<template>
  <OCascaderV2 v-model="val" :options="options" clearable placeholder="请选择" />
</template>
```

**场景 2：多选**
适用于：多标签筛选
```vue
<script setup>
import { ref } from 'vue';
const val = ref([]);
const options = [
  { label: '前端', value: 'fe', children: [
    { label: 'Vue', value: 'vue' },
    { label: 'React', value: 'react' },
  ] },
];
</script>
<template>
  <OCascaderV2 v-model="val" :options="options" multiple clearable placeholder="请选择多个" />
</template>
```

**场景 3：多选 + maxTagCount**
适用于：多选标签过多时折叠显示
```vue
<script setup>
import { ref } from 'vue';
import type { SelectOptionT } from '@opensig/opendesign';
const val = ref([]);
const foldLabel = (tags: Array<SelectOptionT>) => `还有 ${tags.length} 项`;
</script>
<template>
  <OCascaderV2 v-model="val" :options="options" multiple :max-tag-count="1" :fold-label="foldLabel" show-fold-tags="hover" clearable />
</template>
```

**场景 4：可搜索**
适用于：选项较多需要搜索
```vue
<OCascaderV2 v-model="val" :options="options" filterable clearable placeholder="输入搜索" />
```

**场景 5：emitPath 路径模式**
适用于：需要完整路径数据
```vue
<!-- 单选 emitPath=true: val = ['zj', 'hz', 'xh'] -->
<OCascaderV2 v-model="val" :options="options" emit-path clearable />
<!-- 多选 emitPath=true: val = [['zj', 'hz', 'xh'], ...] -->
<OCascaderV2 v-model="val" :options="options" multiple emit-path clearable />
```

**场景 6：hover 展开**
适用于：层级深节点密集的场景
```vue
<OCascaderV2 v-model="val" :options="options" expand-trigger="hover" clearable />
```

**场景 7：任意层级选中**
适用于：非叶子节点也需要作为独立选中项
```vue
<OCascaderV2 v-model="val" :options="options" allow-select-any-node clearable />
```

**场景 8：选择前拦截**
适用于：选中前需要确认或改写
```vue
<script setup>
const beforeSelect = (value, currentValue) => {
  if (value === 'blocked') return false; // 阻止
  if (value === 'rewrite') return 'new-value'; // 改写
  return true; // 放行
};
</script>
<template>
  <OCascaderV2 v-model="val" :options="options" :before-select="beforeSelect" clearable />
</template>
```

**场景 9：懒加载**
适用于：选项数据异步获取
```vue
<script setup>
import { ref } from 'vue';
const val = ref();
const lazyload = (node, resolve, reject) => {
  if (node.value === null) {
    // 根节点
    setTimeout(() => resolve([{ value: '1', label: 'Option 1', leaf: false }]), 800);
  } else {
    // 子节点
    setTimeout(() => resolve([{ value: '1-1', label: 'Sub 1-1', leaf: true }]), 800);
  }
};
</script>
<template>
  <OCascaderV2 v-model="val" lazy :lazyload="lazyload" clearable placeholder="请选择" @lazyload-error="(node) => console.log('加载失败', node)" />
</template>
```

**场景 10：Panel 独立使用**
适用于：面板直接嵌入页面
```vue
<script setup>
import { OCascaderV2Panel } from '@opensig/opendesign';
</script>
<template>
  <OCascaderV2Panel v-model="val" :options="options" size="large" />
</template>
```

### 常见 prop 组合速查

| 场景 | 推荐 prop 组合 | 说明 |
|------|---------------|------|
| 基础单选 | `v-model` + `options` + `clearable` | 最常见用法 |
| 多选 | `v-model` + `options` + `multiple` + `clearable` | 多选标签模式 |
| 多选折叠 | `v-model` + `options` + `multiple` + `maxTagCount` + `foldLabel` | 标签过多时 |
| 可搜索 | `v-model` + `options` + `filterable` | 搜索筛选 |
| 路径值 | `v-model` + `options` + `emitPath` | 返回完整路径 |
| hover 展开 | `v-model` + `options` + `expandTrigger="hover"` | 悬停展开子级 |
| 任意节点 | `v-model` + `options` + `allowSelectAnyNode` | 非叶子可选 |
| 懒加载 | `v-model` + `lazy` + `lazyload` | 异步加载选项 |
| 拦截选中 | `v-model` + `options` + `beforeSelect` | 选中前确认 |
| 表单内 | `v-model` + `options` + OFormItem 包裹 | 自动继承校验 |

### 可覆盖的 CSS 变量

在调用处覆盖以下变量调整组件外观，**无需 `:deep` hack**：

**选择器触发器变量**：

| 变量名 | 默认值(large) | 默认值(medium) | 说明 |
|--------|-------------|-------------|------|
| `--cascader-v2-text-size` | `var(--o-font_size-text1)` | `var(--o-font_size-tip1)` | 文字字号 |
| `--cascader-v2-text-height` | `var(--o-line_height-text1)` | `var(--o-line_height-tip1)` | 文字行高 |
| `--cascader-v2-placeholder` | `var(--o-color-info4)` | 同 | 占位文字颜色 |
| `--cascader-v2-icon-color` | `var(--o-color-info3)` | 同 | 图标颜色 |
| `--cascader-v2-icon-size` | `var(--o-icon_size_control-m)` | `var(--o-icon_size_control-xs)` | 图标尺寸 |
| `--cascader-v2-icon-gap` | `8px` | 同 | 图标间距 |
| `--cascader-v2-height` | `var(--o-control_size-l)` | `var(--o-control_size-m)` | 选择框高度 |
| `--cascader-v2-multiple-max-height` | `64px` | `64px` | 多选最大高度 |
| `--cascader-v2-tag-bg-color` | `var(--o-color-control2-light)` | 同 | 标签背景色 |
| `--cascader-v2-tag-radius` | `4px` | 同 | 标签圆角 |
| `--cascader-v2-tag-text-size` | `var(--o-font_size-tip2)` | 同 | 标签字号 |

**面板变量**：

| 变量名 | 默认值(large) | 默认值(medium) | 说明 |
|--------|-------------|-------------|------|
| `--cascader-v2-panel-container-max-height` | `388px` | `293px` | 面板最大高度 |
| `--cascader-v2-panel-container-max-width` | `320px` | 同 | 面板最大宽度 |
| `--cascader-v2-option-padding` | `7px 12px` | `3px 12px` | 选项内边距 |
| `--cascader-v2-option-text-size` | `var(--o-font_size-text1)` | `var(--o-font_size-tip1)` | 选项字号 |
| `--cascader-v2-option-icon-size` | `var(--o-icon_size-m)` | `var(--o-icon_size-xs)` | 选项图标尺寸 |
| `--cascader-v2-option-color` | `var(--o-color-info2)` | 同 | 选项文字颜色 |
| `--cascader-v2-option-color-selected` | `var(--o-color-primary1)` | 同 | 选中文字颜色 |
| `--cascader-v2-option-bg-color-hover` | `var(--o-color-control2-light)` | 同 | 选项悬停背景 |
| `--cascader-v2-option-bg-color-selected` | `var(--o-color-control3-light)` | 同 | 选项选中背景 |

**使用示例**:
```vue
<OCascaderV2 v-model="val" :options="options" style="--cascader-v2-height: 40px; --cascader-v2-icon-gap: 12px" />
```

### 响应式行为表

| 维度 | pad_v ~ laptop | > laptop |
|------|---------------|---------|
| large 选择框高度 | 36px | `--o-control_size-l` |
| large 选择框字号 | tip1 | text1 |
| large 选择框图标 | control-s | control-m |
| large 面板选项 padding | 6px 12px | 7px 12px |
| large 面板选项字号 | tip1 | text1 |
| large 面板选项图标 | s | m |
| medium 选择框高度 | 28px | `--o-control_size-m` |
| medium 选择框图标 | control-xs | control-xs |
| 触控设备 expandTrigger | 强制 click | 保留原设置 |

### 组件布局结构

**OCascaderV2 触发器**
```yaml
layout:
  component: InBox.o-cascader-v2
  direction: horizontal
  size: 由 size/variant/color/round 决定
  regions:
    - name: value-list
      element: OScroller.o-cascader-v2-tags-scroller
      wrap-class: o-cascader-v2-value-list
      children:
        - name: single-input
          condition: 非多选 或 多选无选中值
          element: input.o-cascader-v2-input
          style: readonly=!filterable
        - name: multiple-tags
          condition: 多选 + 有选中值
          element: div.o-cascader-v2-tags-wrap
          children:
            - div.o-cascader-v2-tag(循环valueListDisplay)
              - span.o-cascader-v2-tag-text
              - div.o-cascader-v2-tag-remove(IconClose)
            - OPopover(折叠tag, condition: maxTagCount 有值且超限)
              - div.o-cascader-v2-tag(foldLabel / #tagFold)
              - 浮层: div.o-cascader-v2-tags(折叠tag列表)
            - input.o-cascader-v2-input(filterable模式下)
              - span.o-cascader-v2-input-mirror(宽度测量)
    - name: suffix
      element: div.o-cascader-v2-suffix
      children:
        - div.o-cascader-v2-suffix-icon
          - IconLoading(loading=true, 旋转)
          - IconClose(clearable + hover, 替换箭头)
          - IconChevronDown(下拉箭头, #arrow插槽)
        - slot: suffix(active:isSelecting)
```

**OCascaderV2Panel 正常模式**
```yaml
layout:
  component: div.o-cascader-v2-panel
  direction: horizontal(flex)
  regions:
    - column*1~N(循环panelInfo)
      - ODivider(direction=v, 列间分隔, index>0时)
      - OScroller.o-cascader-v2-panel-scroller
        - ul.o-cascader-v2-options
          - li.o-cascader-v2-option(循环columnInfo)
            - OCascaderV2Label:
              - ORadio(单选+allowSelectAnyNode)
              - OCheckbox(多选)
              - span.o-cascader-v2-option-label(文本)
              - span.o-cascader-v2-option-arrow(IconChevronRight/IconLoading)
              - OPopover(文本溢出提示)
```

**OCascaderV2Panel 筛选模式**
```yaml
layout:
  component: div.o-cascader-v2-panel
  direction: single-column
  regions:
    - OScroller(搜索结果列表)
      - ul.o-cascader-v2-options.o-cascader-v2-options-filterable
        - li.o-cascader-v2-option(循环filteredOptions)
          - OCascaderV2Label(labelParts高亮)
    - div.o-cascader-v2-panel-empty(无结果时)
```

### 设计稿识别指南

**视觉特征指纹**

1. 选择框（类似 Select）+ 下拉后多列横向排列菜单（列间竖分隔线） → OCascaderV2
2. 多列菜单中非叶子节点右侧有箭头 → OCascaderV2（expandTrigger:click/hover）
3. 选项左侧有 Checkbox → OCascaderV2（multiple=true）
4. 选项左侧有 Radio → OCascaderV2（!multiple + allowSelectAnyNode=true）
5. 输入框可编辑搜索 + 面板变为单列搜索结果 + 关键词高亮 → OCascaderV2（filterable=true）
6. 非叶子节点半选态（Checkbox indeterminate） → OCascaderV2（multiple + !allowSelectAnyNode）
7. 懒加载节点显示旋转 loading 图标 → OCascaderV2（lazy=true）

**设计 Token → Prop 值映射表**

| 设计稿属性 | 值 / 范围 | 对应 Prop | Prop 值 | 备注 |
|-----------|----------|----------|---------|------|
| 选择框边框 | 有边框 | variant | `'outline'` | 默认 |
| 选择框背景 | 实心填充 | variant | `'solid'` | — |
| 选择框无边框 | 纯文字 | variant | `'text'` | — |
| 圆角 | 全圆角 | round | `'pill'` | — |
| 尺寸 | 大号 | size | `'large'` | 默认 |
| 尺寸 | 中号 | size | `'medium'` | — |
| 选项有 Checkbox | 多选 | multiple | `true` | — |
| 选项有 Radio | 单选任意节点 | allowSelectAnyNode | `true` | — |
| hover 展开子级 | 悬停展开 | expandTrigger | `'hover'` | 触控降级为click |
| 输入框显示全路径 | 浙江/杭州/西湖 | showAllLevels | `true` | 默认 |
| 输入框只显示叶子 | 西湖 | showAllLevels | `false` | — |
| 可搜索 | 输入框可编辑 | filterable | `true` | — |
| 清除按钮 | 右侧 × 图标 | clearable | `true` | — |
| 加载状态 | 旋转加载图标 | loading | `true` | — |
| 父节点半选 | Checkbox indeterminate | — | multiple + !allowSelectAnyNode 自动 | — |

**易混淆组件区分表**

| 本组件 | 易混淆组件 | 关键区分依据 |
|--------|-----------|-------------|
| OCascaderV2 | OCascader | V2 面板为多列横向排列（列间竖分隔线），旧版为树形展开 |
| OCascaderV2 | OSelect | Cascader 是级联多级选择，Select 是单级选择 |

### 版本变更记录

| 版本 | 变更类型 | 变更内容 |
|------|---------|---------|
| 1.2.4 | 新增 | OCascaderV2 / OCascaderV2Panel / OCascaderV2Label 组件首次发布，支持单选/多选/可搜索/懒加载/选择前拦截/路径值/任意层级选中 |
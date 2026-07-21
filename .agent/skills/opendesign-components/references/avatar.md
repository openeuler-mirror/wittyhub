> ← [组件索引](../SKILL.md#组件索引) · [README](../../../README.md)

# OAvatar 头像

## Part A：设计理解卡

OAvatar 是头像/头像组展示组件，用于显示用户头像图片、名称首字符或默认图标。支持图片/文字/默认图标三种内容模式、可点击交互遮罩、名称自定义渲染，以及 OAvatarGroup 头像组（水平堆叠与对称网格两种布局、溢出省略或计数显示）。

### 外观

**size**（属性）：头像尺寸。支持数字（自动加 px）、CSS 变量（如 `var(--o-icon_size-4xl)`）或带单位的字符串（如 `56px`）。OAvatar 默认 `var(--o-icon_size-4xl)`，OAvatarGroup 默认 `var(--o-icon_size-s)`。

**background**（属性）：头像背景色。仅在文字模式（有 name 无 url）时生效。未指定时，文字模式背景随机分配 `--o-color-auxiliary1~8` 之一；图片模式背景为 `--o-color-fill2`。

**objectFit**（属性）：图片填充方式。"fill" 默认拉伸、"contain" 保持比例完整显示、"cover" 保持比例裁剪填满、"none" 原始大小、"scale-down" 取 contain 和 none 较小者。默认 fill。

### 内容类型

**url**（属性）：头像图片地址。有 url 时展示图片；图片加载失败回退为默认头像图标，并触发 error 事件。

**name**（属性）：头像名称。无 url 时展示 name 的首字符；无 url 无 name 时展示默认头像图标（IconAvatar）。

**nameFormatter**（属性）：名称自定义渲染函数。接收 `{ name?: string }` 对象，返回 VNode。优先级高于首字符显示和 `#name` 插槽的默认内容。

### 交互

**clickable**（属性）：是否可点击。开启后 hover 时显示半透明遮罩层（`--avatar-mask`）+ 编辑图标（IconEdit）。遮罩层 opacity 从 0 到 1 过渡，transition 为 `var(--o-duration-s) var(--o-easing-standard)`。默认关闭。

### 头像组（OAvatarGroup）

**urlList**（属性）：头像列表数据，每项为 `{ url?, name?, background? }` 的 AvatarItem 对象。

**layout**（属性）：布局模式。"horizontal" 水平堆叠（最多显示 2 个真实头像 + 1 个溢出提示，负 margin 重叠排列）、"symmetric" 对称网格（1 个水平居中、2 个横排、3 个等腰三角、4 个 2x2 方阵、>=5 个 2x2 + 溢出）。默认 horizontal。

**overflowType**（属性）：溢出头像展示方式。"ellipsis" 显示省略号图标（IconEllipsis）、"count" 显示 +N 数量（超过 99 显示 99+）。默认 ellipsis。

**nameFormatter**（属性）：组内头像的名称渲染函数，透传至每个 OAvatar。

**objectFit**（属性）：组内头像的图片填充方式，透传至每个 OAvatar。

### 事件

**click**（OAvatar 事件）：点击头像时触发。仅在 clickable=true 时生效。

**error**（OAvatar 事件）：图片加载失败时触发。

**load**（OAvatar 事件）：图片加载成功时触发。

### 插槽

**name**（OAvatar 插槽）：自定义名称文字区域。默认回退内容为 nameFormatter 渲染结果或 `name[0]` 首字符。

**triggerIcon**（OAvatar 插槽）：自定义可点击遮罩层上的触发图标。默认为 IconEdit 编辑图标。

**more**（OAvatarGroup 插槽）：自定义溢出头像的内容。默认回退为省略号图标或 +N 计数文字。

📱 **响应式行为**：Avatar 本身无内置响应式断点逻辑。size 属性可传入 CSS 变量实现响应式尺寸（如 `var(--o-icon_size-4xl)` 受全局 token 响应式规则影响）。OAvatarGroup 的 symmetric 布局在小尺寸下 grid gap 为 3.5px，视觉间距随 avatar-size 缩放。

🧩 **布局结构**：OAvatar 根元素为 `div.o-avatar.o-avatar-circle`（始终圆形），内部按内容类型渲染 `<img>` / `<span>` 文字 / `<IconAvatar>` 默认图标，clickable 时叠加 `.o-avatar-trigger-icon` 遮罩层。OAvatarGroup 根元素为 `div.o-avatar-group`，根据 layout 切换 `.o-avatar-group-horizontal`（flex row-reverse + 负 margin）或 `.o-avatar-group-symmetric`（grid 2x2 / 1x1 / 三角形布局）。
```yaml
# 简化结构摘要（完整版见 Part B）
direction: OAvatar 单个圆形容器; OAvatarGroup horizontal 为水平堆叠，symmetric 为网格
regions(OAvatar): [img/文字/默认图标(主内容), trigger-icon(可点击遮罩,可选)]
regions(OAvatarGroup): [more(溢出提示,可选), avatar*1~4(真实头像)]
note: horizontal 布局溢出提示在头部（DOM 反转排列），symmetric 溢出提示在尾部
```

🔍 **设计稿识别指南**：
- **视觉特征指纹**：圆形容器（border-radius: 50%），内含图片/单字符/默认头像图标；多个人头圆形部分重叠排列（horizontal）或 2x2 网格排列（symmetric）
- **内容模式判定**：有图片 = url 模式；单字符文字 + 随机彩色背景 = name 模式；灰色背景 + 人头轮廓图标 = 默认模式
- **Token → Prop 映射**：圆形尺寸 48px=size:48 或 size:var(--o-icon_size-4xl)；图片裁剪方式=objectFit:cover/contain/fill；hover 有半透明遮罩+编辑图标=clickable:true；多个重叠排列=OAvatarGroup layout:horizontal；2x2 网格=OAvatarGroup layout:symmetric；溢出省略号=overflowType:ellipsis；溢出+N=overflowType:count
- **易混淆组件区分**：与 OIcon 区别——Avatar 是圆形容器（固定宽高相等），Icon 是纯图标无容器；与 OBadge 区别——Badge 是附加在元素角标的小标记，Avatar 是独立的用户标识展示

---

## Part B：代码调用参考

### 导入方式

```vue
<script setup>
import { OAvatar, OAvatarGroup } from '@opensig/opendesign';
</script>
```

### OAvatar Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| size | `number | string` | — | `'var(--o-icon_size-4xl)'` | 1.2.3 | 尺寸，支持数字/变量/带单位值 |
| background | `string` | — | — | 1.2.3 | CSS background（文字模式未指定时随机取 auxiliary 色） |
| url | `string` | — | — | 1.2.3 | 图片地址 |
| name | `string` | — | — | 1.2.3 | 名称（无 url 时显示首字符） |
| nameFormatter | `(data: { name?: string }) => VNode` | — | — | 1.2.3 | 名称渲染函数 |
| clickable | `boolean` | — | `false` | 1.2.3 | 可点击，hover 显示遮罩 |
| objectFit | `'fill' | 'contain' | 'cover' | 'none' | 'scale-down'` | — | `'fill'` | 1.2.3 | 图片填充方式 |

### OAvatar Events 表

| 事件名 | 参数 | 引入版本 | 触发时机 |
|--------|------|---------|---------|
| click | `(evt: MouseEvent)` | 1.2.3 | 点击头像（仅 clickable=true 时） |
| error | — | 1.2.3 | 图片加载失败 |
| load | — | 1.2.3 | 图片加载成功 |

### OAvatar Slots 表

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| name | — | 无 url 有 name 时渲染 | 名称文字区域 | `nameFormatter` 渲染结果或 `name[0]` 首字符 |
| triggerIcon | — | clickable=true 时渲染 | 遮罩层触发图标 | IconEdit 编辑图标 |

### OAvatarGroup Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 引入版本 | 说明 |
|--------|------|--------|--------|---------|------|
| urlList | `AvatarItem[]` | — | `[]` | 1.2.3 | 头像列表，每项 `{ url?, name?, background? }` |
| size | `number | string` | — | `'var(--o-icon_size-s)'` | 1.2.3 | 组内所有头像的统一尺寸 |
| layout | `'horizontal' | 'symmetric'` | — | `'horizontal'` | 1.2.3 | 布局模式 |
| overflowType | `'ellipsis' | 'count'` | — | `'ellipsis'` | 1.2.3 | 溢出展示方式 |
| nameFormatter | `(data: { name?: string }) => VNode` | — | — | 1.2.3 | 名称渲染函数，透传至每个头像 |
| objectFit | `'fill' | 'contain' | 'cover' | 'none' | 'scale-down'` | — | `'fill'` | 1.2.3 | 图片填充方式，透传至每个头像 |

### OAvatarGroup Slots 表

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| more | — | 溢出数量 > 0 时渲染 | 溢出头像内容 | 省略号图标（ellipsis）或 +N 计数文字（count） |

### 插槽层级关系

```
OAvatar:
  name（名称文字，url 不存在时生效）
  triggerIcon（可点击遮罩图标，clickable=true 时生效）

OAvatarGroup:
  more（溢出头像内容，溢出数量 > 0 时生效）

OAvatarGroup 内部使用 createReusableTemplate 渲染溢出头像，
溢出头像的 #name 插槽由 OAvatarGroup 的 #more 插槽替代。
```

### 典型使用场景与调用模板

**场景 1：图片头像**
适用于：展示用户真实头像
```vue
<OAvatar :size="56" url="https://example.com/avatar.jpg" object-fit="cover" />
```

**场景 2：名称首字符头像**
适用于：无图片时显示用户名首字母
```vue
<OAvatar name="Alice" />
<OAvatar name="Alice" background="#e6f7ff" />
```

**场景 3：默认头像图标**
适用于：无图片无名称时的占位展示
```vue
<OAvatar />
```

**场景 4：可点击头像（编辑头像）**
适用于：点击头像触发编辑操作
```vue
<script setup>
const handleAvatarClick = (e) => {
  console.log('编辑头像');
};
</script>
<template>
  <OAvatar :size="56" url="https://example.com/avatar.jpg" clickable @click="handleAvatarClick" />
</template>
```

**场景 5：自定义名称渲染**
适用于：名称需要显示多字符或自定义样式
```vue
<script setup>
import { h } from 'vue';
const customFormatter = ({ name }) => h('div', { style: { color: '#fff', fontWeight: 'bold' } }, name);
</script>
<template>
  <OAvatar :size="56" name="Alice" :name-formatter="customFormatter" />
</template>
```

**场景 6：头像组 - 水平堆叠**
适用于：协作成员列表、项目参与者等
```vue
<script setup>
const urlList = [
  { url: 'https://example.com/a.jpg', name: 'Alice' },
  { url: 'https://example.com/b.jpg', name: 'Bob' },
  { name: 'Carol' },
  { name: 'Dave' },
  { name: 'Eve' },
];
</script>
<template>
  <OAvatarGroup :url-list="urlList" size="60px" />
  <OAvatarGroup :url-list="urlList" size="60px" overflow-type="count" />
</template>
```

**场景 7：头像组 - 对称网格**
适用于：群组标识、多人协作图标
```vue
<script setup>
const urlList = [
  { url: 'https://example.com/a.jpg', name: 'Alice' },
  { url: 'https://example.com/b.jpg', name: 'Bob' },
  { url: 'https://example.com/c.jpg', name: 'Carol' },
  { url: 'https://example.com/d.jpg', name: 'Dave' },
];
</script>
<template>
  <OAvatarGroup layout="symmetric" :url-list="urlList" size="60px" />
</template>
```

**场景 8：自定义溢出内容**
适用于：头像组溢出需要展示更多信息
```vue
<script setup>
const urlList = Array.from({ length: 10 }, (_, i) => ({ name: `User${i + 1}` }));
</script>
<template>
  <OAvatarGroup :url-list="urlList" size="60px">
    <template #more>
      <span style="font-size: 12px; color: #999">更多...</span>
    </template>
  </OAvatarGroup>
</template>
```

**场景 9：图片加载失败处理**
适用于：头像图片可能加载失败
```vue
<script setup>
import { ref } from 'vue';
const handleError = () => {
  console.log('头像图片加载失败');
};
const handleLoad = () => {
  console.log('头像图片加载成功');
};
</script>
<template>
  <OAvatar url="https://invalid-url.com/avatar.jpg" @error="handleError" @load="handleLoad" />
</template>
```

### 常见 prop 组合速查

| 场景 | 推荐 prop 组合 | 说明 |
|------|---------------|------|
| 用户头像 | `url` + `object-fit="cover"` + `size` | 最常见用法 |
| 名称头像 | `name` + `background`(可选) | 随机彩色背景 + 首字符 |
| 可编辑头像 | `url` + `clickable` + `@click` | hover 显示编辑遮罩 |
| 头像组默认 | `urlList` + `size` | 水平堆叠 + 省略号溢出 |
| 头像组计数 | `urlList` + `size` + `overflow-type="count"` | 水平堆叠 + +N 溢出 |
| 头像组网格 | `urlList` + `size` + `layout="symmetric"` | 对称网格排列 |
| 自定义名称 | `name` + `nameFormatter` | 全名或多字符渲染 |

### 可覆盖的 CSS 变量

在调用处覆盖以下变量调整组件外观，**无需 `:deep` hack**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `--avatar-size` | prop size 的 normalize 结果 | 头像宽高（始终圆形，width = height） |
| `--avatar-bg` | 文字模式随机 auxiliary 色；图片模式 `--o-color-fill2` | 头像背景色 |
| `--avatar-color` | `var(--o-color-white)` | 头像文字颜色 |
| `--avatar-mask` | `var(--o-color-mask1)` | 可点击遮罩层背景色 |
| `--avatar-border` | `2px solid var(--o-color-fill2)` | 头像组中头像的白色边框 |

**使用示例**:
```vue
<OAvatar name="Alice" style="--avatar-bg: #1a73e8; --avatar-color: #fff" />
<OAvatarGroup style="--avatar-border: 3px solid #fff" :url-list="urlList" size="60px" />
```

### 响应式行为表

| 维度 | 行为 | 备注 |
|------|------|------|
| size 传入 CSS 变量 | 受全局 token 响应式规则影响 | 如 `var(--o-icon_size-4xl)` 在不同断点可能不同 |
| OAvatarGroup symmetric | grid gap 固定 3.5px | 小尺寸头像下间距可能偏大，建议手动调整 |
| OAvatarGroup horizontal | 负 margin 按 `--avatar-size * -4/24` 计算 | 随 avatar-size 缩放 |

### 组件布局结构

**OAvatar**
```yaml
layout:
  component: div.o-avatar.o-avatar-circle
  direction: centered(flex)
  align: center
  size: var(--avatar-size)  # width = height, 始终圆形
  font-size: calc(var(--avatar-size) * 0.4)  # 文字模式字号
  regions:
    - name: image
      element: img
      condition: url 存在且未加载失败
      style: objectFit 由 prop 控制
    - name: text
      condition: 无 url 有 name 时
      children:
        - { type: slot, name: name, fallback: "nameFormatter渲染 或 name[0]" }
    - name: default-icon
      element: IconAvatar.o-avatar-default-icon
      condition: 无 url 无 name，或图片加载失败时
    - name: trigger-icon
      element: div.o-avatar-trigger-icon
      condition: clickable=true
      opacity: 0 → 1(hover时)
      children:
        - { type: slot, name: triggerIcon, fallback: "IconEdit" }
  variants:
    img-loaded: { class: o-avatar-img, bg: var(--o-color-fill2) }
    default: { class: o-avatar-default, bg: 无/透明 }
    text: { class: o-avatar-text, bg: 随机auxiliary色或background }
    clickable: { class: o-avatar-clickable }
```

**OAvatarGroup - horizontal 布局**
```yaml
layout:
  component: div.o-avatar-group.o-avatar-group-horizontal
  direction: horizontal(flex, row-reverse)
  align: center
  regions:
    - name: more-overflow
      condition: 溢出数量 > 0
      element: OAvatar.o-avatar-group-more  # 位于头部（DOM首位）
      children:
        - { type: slot, name: more, fallback: "IconEllipsis 或 +N文字" }
    - name: avatars
      element: OAvatar(循环, reversed排列)
      count: 最多 2 个真实头像
      style: margin-left: calc(--avatar-size * -4/24), border: 2px solid fill2
  overflow:
    max_visible: 3  # 2 真实 + 1 溢出
    more_position: 首位(DOM反转排列)
```

**OAvatarGroup - symmetric 布局**
```yaml
layout:
  component: div.o-avatar-group.o-avatar-group-symmetric
  direction: grid(2x2 或自适应)
  gap: 3.5px
  variants:
    single(total<2): { grid-template-columns: 1fr }
    triangle(total=3): { grid-template-columns: 1fr 1fr, 首项跨两列居中 }
    square(total=4): { grid-template-columns: 1fr 1fr }
  regions:
    - name: avatars
      element: OAvatar(循环)
      count: 最多 3 个真实头像
    - name: more-overflow
      condition: 溢出数量 > 0
      element: OAvatar.o-avatar-group-more  # 位于尾部
      children:
        - { type: slot, name: more, fallback: "IconEllipsis 或 +N文字" }
  overflow:
    max_visible: 4  # 3 真实 + 1 溢出
    more_position: 末位
```

### 设计稿识别指南

**视觉特征指纹**

1. 单个圆形容器 + 内含图片 → 匹配 OAvatar（url 模式）
2. 单个圆形容器 + 内含单字符文字 + 彩色背景 → 匹配 OAvatar（name 模式）
3. 单个圆形容器 + 内含人头轮廓图标 + 灰色背景 → 匹配 OAvatar（默认模式）
4. hover 时圆形上叠加半透明遮罩 + 编辑/铅笔图标 → 匹配 OAvatar（clickable=true）
5. 多个圆形部分重叠排列（人头像叠在一起） → 匹配 OAvatarGroup（layout=horizontal）
6. 2x2 网格排列的圆形头像 → 匹配 OAvatarGroup（layout=symmetric）
7. 等腰三角形排列（1上2下）的圆形头像 → 匹配 OAvatarGroup（layout=symmetric, 3 项）
8. 溢出位置显示省略号图标 → 匹配 OAvatarGroup（overflowType=ellipsis）
9. 溢出位置显示 +N 数字 → 匹配 OAvatarGroup（overflowType=count）

**设计 Token → Prop 值映射表**

| 设计稿属性 | 值 / 范围 | 对应 Prop | Prop 值 | 备注 |
|-----------|----------|----------|---------|------|
| 圆形尺寸 | 48px / 56px 等 | size | `48` / `56` 等 | 数字自动加 px |
| 圆形尺寸 | CSS 变量 | size | `'var(--o-icon_size-4xl)'` 等 | 默认值 |
| 图片裁剪 | 保持比例裁剪填满 | objectFit | `'cover'` | 最常用 |
| 图片裁剪 | 保持比例完整显示 | objectFit | `'contain'` | — |
| 图片裁剪 | 拉伸填满 | objectFit | `'fill'` | 默认 |
| 文字背景色 | 随机彩色 | background | — | 不指定时随机 |
| 文字背景色 | 指定颜色 | background | `'#e6f7ff'` 等 | — |
| hover 遮罩 | 半透明 + 编辑图标 | clickable | `true` | — |
| 多人重叠排列 | 水平堆叠 | layout | `'horizontal'` | 默认 |
| 多人网格排列 | 2x2/三角/横排 | layout | `'symmetric'` | — |
| 溢出省略号 | ...图标 | overflowType | `'ellipsis'` | 默认 |
| 溢出+N | +2 / 99+ 等 | overflowType | `'count'` | — |

**易混淆组件区分表**

| 本组件 | 易混淆组件 | 关键区分依据 |
|--------|-----------|-------------|
| OAvatar | OIcon | Avatar 是圆形容器（固定宽高相等），Icon 是纯图标无固定容器 |
| OAvatar | OBadge | Badge 是附加在元素角标的小标记数字，Avatar 是独立的用户标识圆形展示 |
| OAvatarGroup | 多个 OAvatar | AvatarGroup 有溢出逻辑和堆叠/网格布局，多个独立 Avatar 无溢出处理 |
| OAvatar(文字) | OTag | Tag 是带边框的标签卡片，Avatar 是圆形纯色背景无边框 |

### 版本变更记录

| 版本 | 变更类型 | 变更内容 |
|------|---------|---------|
| 1.2.3 | 新增 | OAvatar 与 OAvatarGroup 组件首次发布，支持图片/文字/默认三种模式、clickable 交互、horizontal/symmetric 布局 |
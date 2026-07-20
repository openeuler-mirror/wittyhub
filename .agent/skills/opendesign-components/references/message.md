> ← [组件索引](../SKILL.md#组件索引) · [README](../../../README.md)

# OMessage 消息提示

## Part A：设计理解卡

OMessage 是消息提示组件，用于操作反馈信息的展示。支持两种使用方式：
- **组件式调用 (`<OMessage>`)**：仅适用于行内/固定位置的静态提示（如页面顶部公告）
- **命令式调用 (`useMessage()`)**：推荐用于操作后的动态反馈消息（如表单提交反馈）

组件支持五种状态、彩色背景模式、自动关闭、手动关闭等功能。

### 状态

**status**（属性）：消息状态类型。"info" 信息提示、"success" 成功、"warning" 警告、"danger" 危险/错误、"loading" 加载中。不同状态对应不同颜色和图标。默认 info。

**colorful**（属性）：是否使用彩色背景。开启后消息背景色跟随状态颜色变化，并在左侧显示彩色侧边条。默认关闭。

### 显示控制

**visible**（属性）：消息是否可见（v-model 双向绑定）。

**defaultVisible**（属性）：非受控模式下消息是否默认可见。默认可见。

**duration**（属性）：消息自动关闭的持续时间（毫秒）。未设置或小于等于 0 时不自动关闭。鼠标悬停在消息上时暂停计时。

**closable**（属性）：是否显示关闭按钮，允许手动关闭。默认关闭。

**beforeClose**（属性）：关闭前的钩子函数。返回 true 允许关闭，返回 false 阻止关闭。支持异步。

### 内容

**title**（属性）：消息标题文字。

**title 插槽**（插槽）：替换标题区域。使用后 title 属性失效。

**default 插槽**（插槽）：消息正文内容。

**icon 插槽**（插槽）：替换状态图标区域。

### 事件

**duration-end**（事件）：自动关闭计时结束时触发。

**close**（事件）：消息关闭时触发。

---

### useMessage 命令式调用场景

**何时使用命令式 `useMessage()`**：
- ✅ 操作反馈：表单提交、数据删除等操作的结果提示
- ✅ 动态消息：根据用户操作或接口响应动态显示消息
- ✅ 临时通知：自动消失的消息，不需要常驻页面
- ✅ 定位提示：需要在特定元素附近显示的提示（如表单验证错误）

**为什么不用组件式 `<OMessage>`**：
- 组件式声明了后无法动态控制显示/隐藏，必须维护 visible 状态
- 组件式需手动管理多条消息，无法复用 useMessage 内置的消息栈管理
- 组件式定位受限于 Vue 组件树，无法灵活在任意目标元素附近显示

📱 **响应式行为**：在笔记本尺寸及以下（≤1440px），消息内边距、文字大小、图标尺寸缩小；在平板横屏及以下（≤1200px），消息间距进一步缩小；在平板竖屏及以下（≤840px），带标题的消息标题文字缩小、图标缩至最小、彩色模式侧边条变窄。

🧩 **布局结构**：消息条水平排列，从左到右依次为：彩色侧边条（仅 colorful 模式，宽 4px）、状态图标区、主内容区（标题 + 正文纵向排列）、关闭按钮区（仅 closable 时显示）。消息整体有圆角和阴影（colorful 模式无阴影），内边距 8px 16px，图标与内容间距 8px，关闭按钮间距 16px。
```yaml
# 简化结构摘要（完整版见 Part B）
direction: horizontal
regions: [sidebar(彩色侧边条,仅colorful), icon(状态图标), main(标题+正文), close(关闭按钮,仅closable)]
```

🔍 **设计稿识别指南**：
- **视觉特征指纹**：页面顶部或指定区域出现的水平通知条，左侧带状态图标（信息/成功/警告/错误/加载），右侧可能有关闭按钮；有阴影或彩色背景变体 → 匹配 OMessage
- **Token → Prop 映射**：蓝色信息图标 → status="info"；绿色勾号 → status="success"；橙色感叹号 → status="warning"；红色叉号 → status="danger"；旋转加载图标 → status="loading"；左侧彩色边条+彩色背景 → colorful；右侧 X 按钮 → closable
- **易混淆组件区分**：与 OToast 区分——OMessage 通常位于顶部、带状态颜色语义（success/warning/danger），OToast 是深色背景轻提示、默认底部显示、无颜色语义；与 ODialog 区分——OMessage 是非模态轻量提示不阻断操作，ODialog 是模态对话框需用户处理后才能继续

---

## Part B：代码调用参考

### 导入方式

```vue
<script setup>
import { OMessage, useMessage } from '@opensig/opendesign';
</script>
```

### 类型定义

```typescript
type MessageStatusT = 'info' | 'success' | 'warning' | 'danger' | 'loading';
type MessagePositionT = 'top' | 'bottom';

type MessageParamsT = Partial<MessagePropsT & {
  content: string | VNode | Component;
  position: MessagePositionT;
  targetAlign?: 'center' | 'left' | 'right';
  icon: VNode | Component;
  onDurationEnd: () => void;
  onClose: (ev?: MouseEvent) => void;
}>;
```

### OMessage Props 表

| 参数名 | 类型 | 可选值 | 默认值 | 说明 | 引入版本 |
|--------|------|--------|--------|------|--------|
| visible | `boolean` | — | `undefined` | 是否可见（v-model） | — |
| defaultVisible | `boolean` | — | `true` | 默认可见 | — |
| status | `MessageStatusT` | `'info'` / `'success'` / `'warning'` / `'danger'` / `'loading'` | `'info'` | 状态 | — |
| colorful | `boolean` | — | `false` | 彩色背景 | — |
| duration | `number` | — | — | 自动关闭时间（ms） | — |
| closable | `boolean` | — | `false` | 可手动关闭 | — |
| beforeClose | `() => Promise<boolean> \| boolean` | — | — | 关闭前钩子 | — |
| title | `string` | — | — | 标题 | — |

### Events 表

| 事件名 | 参数 | 触发时机 |
|--------|------|---------|
| update:visible | `(val: boolean)` | 显示状态变化时 |
| duration-end | — | 自动关闭计时结束 |
| close | `(ev?: MouseEvent)` | 消息关闭时 |

### Slots 表

| 插槽名 | Slot Props | 触发条件 | 替换范围 | 回退内容 |
|--------|-----------|---------|---------|---------|
| default | — | 始终 | 消息正文 | 无 |
| icon | — | 始终 | 状态图标 | 对应 status 的默认图标 |
| title | — | 有 title prop 或 title 插槽时 | 标题文字 | `{{ title }}` |

### 暴露方法

| 方法名 | 参数 | 说明 |
|--------|------|------|
| close(ev?) | `ev?: MouseEvent` | 关闭消息 |

### useMessage API

```typescript
const message = useMessage(target);
// target?: string | ComponentPublicInstance | HTMLElement | Ref<...>
//          可选，为指定元素附近显示消息；省略时消息在页面指定位置显示

message.show(params);    // 显示消息，params 由status自定义或传入，返回关闭函数
message.info(params);    // info 状态消息
message.success(params); // success 状态消息
message.warning(params); // warning 状态消息
message.danger(params);  // danger 状态消息
message.loading(params); // loading 状态消息
message.close();         // 关闭本实例所有消息
message.closeAll();      // 关闭所有实例的全部消息
```

#### useMessage params 参数详解

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| content | `string \| VNode \| Component` | 否 | — | 消息内容。可直接传字符串作为 params（如 `message.success('保存成功')`）；或在对象中指定 |
| status | `MessageStatusT` | 否 | `'info'` | 消息状态（仅 `show()` 需传，其他方法自动设定） |
| position | `'top' \| 'bottom'` | 否 | `'top'` | 相对目标元素的位置：'top' 目标上方，'bottom' 目标下方 |
| targetAlign | `'center' \| 'left' \| 'right'` | 否 | `'center'` | 消息相对目标元素的水平对齐方式 |
| duration | `number` | 否 | `3000` | 自动关闭时间（毫秒）。0 或负数时不自动关闭 |
| icon | `VNode \| Component` | 否 | — | 自定义消息图标，不传时根据 status 显示默认图标 |
| onDurationEnd | `() => void` | 否 | — | 自动关闭计时完成时的回调函数 |
| onClose | `(ev?: MouseEvent) => void` | 否 | — | 消息关闭时的回调函数，可获取关闭事件 |

#### params 传参形式

> ⚠️ **版本说明**：字符串简写形式（`message.success('...')`）从 **v1.1.0** 开始支持。v1.0.x 及以前版本只接受对象形式，传字符串会报 TS 类型错误。

```typescript
// 形式 1：字符串（简洁写法，v1.1.0+ 支持）
message.success('保存成功');
message.warning('已发送，请检查邮箱');

// 形式 2：对象（全版本支持，推荐）
message.success({
  content: '保存成功',
  duration: 5000,
  onClose: () => console.log('消息已关闭'),
});

// 形式 3：指定位置和对齐
const submitBtn = ref<HTMLElement>();
const message = useMessage(submitBtn);
message.success({
  content: '提交成功',
  position: 'bottom',
  targetAlign: 'right', // 按钮右下方显示
});
```

> **使用指导**：
> - **页面全局消息**：`useMessage()` 无参调用，消息在页面顶部显示
> - **局部元素反馈**：`useMessage(targetEl)` 指定目标元素，消息紧邻该元素显示
> - **自动消失**：默认 3 秒后自动关闭；手动永驻传 `duration: 0`

### 典型使用场景与调用模板

**场景 1：页面公告（组件式，固定位置）**
适用于：页面始终显示的公告/提示（不推荐用于操作反馈）
```vue
<OMessage status="info" colorful>重要公告：系统升级中</OMessage>
<OMessage status="warning" closable :duration="5000">警告：敏感操作需确认</OMessage>
```

**场景 2：带标题详情（组件式，内联）**
适用于：需要标题+详情的静态提示区域（仍是组件式，非命令式）
```vue
<OMessage status="danger" colorful title="操作失败">
  您的账户存在异常，请联系客服处理。
</OMessage>
```

**场景 3：操作反馈（命令式，全局）** ⭐ **推荐**
适用于：表单提交、删除、保存等操作后的动态反馈
```vue
<script setup>
import { useMessage, OButton } from '@opensig/opendesign';
const message = useMessage(); // 无参数，消息显示在页面顶部

const handleSave = async () => {
  try {
    await api.save(data);
    message.success('保存成功');
  } catch (err) {
    message.danger('保存失败，请稍后重试');
  }
};
</script>
<template>
  <OButton @click="handleSave">保存</OButton>
</template>
```

**场景 4：定位提示（命令式，元素附近）** ⭐ **推荐**
适用于：表单验证错误、输入框反馈等需要定位在特定元素附近的提示
```vue
<script setup>
import { useTemplateRef } from 'vue';
import { useMessage } from '@opensig/opendesign';

const passwordInput = useTemplateRef('password');
const message = useMessage(passwordInput); // 指定目标元素

const validatePassword = (pwd: string) => {
  if (pwd.length < 8) {
    message.warning({
      content: '密码长度不能少于 8 位',
      position: 'bottom',
      targetAlign: 'left',
    });
    return false;
  }
  return true;
};
</script>
<template>
  <input ref="password" type="password" placeholder="请输入密码" />
</template>
```

**场景 5：加载状态（命令式，手动关闭）**
适用于：长时间操作（如文件上传、大数据处理），需要显示加载中并由程序控制关闭时机
```vue
<script setup>
import { useMessage } from '@opensig/opendesign';

const message = useMessage();
let closeLoading: (() => void) | null = null;

const handleUpload = async (file: File) => {
  // 显示加载消息，duration: 0 表示不自动关闭
  closeLoading = message.loading({
    content: '上传中，请稍候...',
    duration: 0,
  });

  try {
    await api.upload(file);
    closeLoading?.(); // 手动关闭加载提示
    message.success('上传成功');
  } catch (err) {
    closeLoading?.();
    message.danger('上传失败');
  }
};
</script>
```

### 使用方式速查

| 场景 | 使用方式 | 说明 | 何时选择 |
|------|---------|------|---------|
| **全局操作反馈** | `useMessage()` + `.success()` / `.danger()` | 命令式，消息在页面顶部 | ⭐ 最常见：表单提交、保存、删除等操作 |
| **元素附近提示** | `useMessage(target)` + `.warning()` + `position/targetAlign` | 命令式，定位在目标元素 | 表单验证错误、输入框校验提示 |
| **永驻公告** | `<OMessage status="..." colorful>` | 组件式，嵌入模板 | ⚠️ 仅用于始终显示的页面公告 |
| **加载中** | `useMessage().loading({ duration: 0 })` 返回 close 函数 | 命令式，需手动关闭 | 长时间操作（上传、处理）|
| **可关闭弹窗** | `useMessage().success({ ... })` 返回 close 函数 | 命令式，也可点击关闭 | — |
| **带标题消息** | 组件式 `<OMessage title="...">` 或命令式对象含 content | 两种方式都支持 | 组件式用于公告；命令式应使用普通文本 |

> ⚠️ **重要提醒**：
> - **优先使用 `useMessage()`**，它自动管理消息栈和定位
> - **仅当消息需要始终显示在页面某处时才用组件式 `<OMessage>`**（如页面公告）
> - **不要用组件式处理操作反馈**，那样需要手动维护 visible 状态且无法复用消息栈管理

### 可覆盖的 CSS 变量

在调用处覆盖以下变量调整组件外观，**无需 `:deep` hack**：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `--message-color` | `var(--o-color-info2)` | 消息文字颜色 |
| `--message-text-size` | `var(--o-font_size-text1)` | 正文字号 |
| `--message-text-height` | `var(--o-line_height-text1)` | 正文行高 |
| `--message-bg-color` | `var(--o-color-fill2)` | 消息背景色 |
| `--message-shadow` | `var(--o-shadow-2)` | 消息阴影（colorful 模式为 none） |
| `--message-align` | `start` | 内容对齐方式 |
| `--message-radius` | `var(--o-radius_control-s)` | 圆角 |
| `--message-padding` | `8px 16px` | 内边距 |
| `--message-icon-size` | `var(--o-icon_size_control-m)` | 状态图标尺寸 |
| `--message-icon-gap` | `8px` | 图标与内容的间距 |
| `--message-icon-gap-suffix` | `16px` | 内容与关闭按钮的间距 |
| `--message-icon-close-color` | `var(--o-color-info2)` | 关闭按钮图标颜色 |
| `--message-icon-close-color-hover` | `var(--o-color-info1)` | 关闭按钮悬停颜色 |
| `--message-icon-close-color-active` | `var(--o-color-info1)` | 关闭按钮激活颜色 |
| `--message-word-break` | `break-word` | 文字断行方式 |
| `--message-text-align` | `center` | 文字水平对齐（有标题+正文时为 left） |
| `--message-gap` | `16px` | 多条消息之间的间距 |
| `--message-sidebar-width` | `4px`（colorful 模式） | 彩色侧边条宽度 |
| `--message-list-offset` | `32px` | 消息列表距屏幕边缘的偏移 |

**使用示例**:
```vue
<OMessage status="success" style="--message-radius: 8px; --message-padding: 12px 20px">操作成功</OMessage>
```

### 响应式行为表

| 维度 | ≤840px | 841–1200px | 1201–1440px | >1440px |
|------|--------|-----------|-------------|---------|
| 内边距 | 4px 12px | — | 7px 12px | 标准 |
| 文字 | — | — | tip1 | 标准 |
| 图标 | 控件 xs | — | 控件 s | 标准 |
| 间距 | — | 8px | 12px | 标准 |
| 彩色侧边条 | 3px | — | — | 标准 |
| 带标题时标题字号 | tip2 | — | — | 标准 |

### 组件布局结构

**桌面端 >1440px**
```yaml
layout:
  direction: horizontal
  align: center
  border-radius: var(--o-radius_control-s)
  background: var(--o-color-fill2)
  shadow: var(--o-shadow-2)  # colorful 模式无阴影
  padding: 8px 16px
  gap: 8px  # --message-icon-gap
  regions:
    - name: sidebar
      condition: colorful === true
      width: 4px  # --message-sidebar-width
      height: 100%
      background: 跟随 status 颜色
    - name: icon
      children:
        - { type: slot, name: icon }  # 默认根据 status 显示对应图标
      icon-size: var(--o-icon_size_control-m)
    - name: main
      flex: 1
      direction: vertical
      children:
        - name: title
          condition: 有 title prop 或 title 插槽
          children:
            - { type: slot, name: title }
        - name: content
          children:
            - { type: slot, name: default }
    - name: close
      condition: closable === true
      gap: 16px  # --message-icon-gap-suffix
      children:
        - { type: icon, name: IconClose }
  variants:
    colorful:
      shadow: none
      background: 跟随 status（info→蓝, success→绿, warning→橙, danger→红, loading→品牌色浅）
    both(有标题+有正文):
      text-size: tip1
      padding: 5px 12px 8px
      title-gap: 5px
    only-title(colorful+仅标题):
      title-size: tip1
      padding: 4px 12px
    only-content(colorful+仅正文):
      text-size: tip1
      padding: 4px 12px
```

**≤1440px (laptop)**
```yaml
# padding: 7px 12px, gap: 12px
# text-size: tip1, icon-size: s
# both: text-size tip2
# only-content: text-size tip2, padding 6px 12px
```

**≤1200px (pad)**
```yaml
# gap: 8px
```

**≤840px (pad_v)**
```yaml
# both: title-size tip2, icon-size xs, padding 4px 12px, title-gap 4px
# colorful: sidebar-width 3px
# only-title: title-size tip2, icon-size xs, padding 4px 12px
# only-content: icon-size xs, padding 4px 12px
```

### 设计稿识别指南

**视觉特征指纹**

1. 页面顶部/指定区域浮现的水平条形通知 + 左侧状态图标 + 可选关闭按钮 → 匹配 OMessage
2. 带圆角、阴影的横条 + 五种状态图标之一（信息/成功/警告/错误/加载） → 匹配 OMessage
3. 左侧彩色竖边条 + 彩色背景 + 状态图标 → 匹配 OMessage（colorful 模式）

**设计 Token → Prop 值映射表**

| 设计稿属性 | 值 / 范围 | 对应 Prop | Prop 值 | 备注 |
|-----------|----------|----------|---------|------|
| 状态图标 | 蓝色圆形 i 图标 | status | `'info'` | 默认值 |
| 状态图标 | 绿色勾号 | status | `'success'` | — |
| 状态图标 | 橙色感叹号 | status | `'warning'` | — |
| 状态图标 | 红色叉号/感叹号 | status | `'danger'` | — |
| 状态图标 | 旋转加载圈 | status | `'loading'` | 图标带旋转动画 |
| 背景色 | 彩色（蓝/绿/橙/红）+ 左侧彩色边条 | colorful | `true` | — |
| 背景色 | 白色/浅色 + 阴影 | colorful | `false` | 默认 |
| 右侧 | X 关闭按钮 | closable | `true` | — |
| 标题行 | 有标题文字 | title | 标题文字 | — |

**易混淆组件区分表**

| 本组件 | 易混淆组件 | 关键区分依据 |
|--------|-----------|-------------|
| OMessage | OToast | OMessage 通常位于顶部、带状态颜色语义（success/warning/danger）、可关闭；OToast 是深色背景轻提示、默认底部、无颜色语义 |
| OMessage | ODialog | OMessage 是非模态轻量提示不阻断操作；ODialog 是模态对话框需用户处理后才能继续 |

---

## 版本变更记录

| 版本 | 变更内容 |
|------|---------|
| v1.1.0 | 新增 `--message-list-top-offset` 和 `--message-list-bottom-offset` CSS 变量；`showMessage` 返回关闭函数；OMessageList 新增 `close` 方法 |
| v0.0.70 | 支持指定目标元素附近显示消息 |


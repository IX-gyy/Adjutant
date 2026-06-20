<template>
  <div
    class="message-item"
    :class="{
      'message-user': message.role === 'user',
      'message-assistant': message.role === 'assistant',
      'message-last': isLast
    }"
  >
    <!-- 副官消息：头像在左 -->
    <template v-if="message.role === 'assistant'">
      <div class="message-avatar">
        <AAvatar
          :size="40"
          :src="isEmperorMessage ? '/emperor_avatar.jpg' : '/adjutant-avatar.ico'"
          :class="isEmperorMessage ? 'emperor-avatar' : 'assistant-avatar'"
        >
          <template #icon><RobotOutlined /></template>
        </AAvatar>
      </div>
      <div class="message-content">
        <div class="message-bubble" :class="{ 'emperor-bubble': isEmperorMessage }" @click="handleLinkClick">
          <div class="message-text" v-html="formattedContent"></div>
        </div>
        <div class="message-actions">
          <div class="message-time">{{ formattedTime }}</div>
          <!-- TTS播放按钮 -->
          <AButton
            v-if="isTtsReady && !isEmperorMessage"
            type="link"
            size="small"
            class="tts-btn"
            :loading="isLoadingTts"
            @click="handleTtsPlay"
          >
            <template #icon>
              <SoundOutlined v-if="!isPlaying" />
              <PauseCircleOutlined v-else />
            </template>
            {{ isPlaying ? '停止' : '朗读' }}
          </AButton>
        </div>
      </div>
    </template>

    <!-- 用户消息：头像在右 -->
    <template v-else>
      <div class="message-content">
        <div class="message-bubble" @click="handleLinkClick">
          <div class="message-text" v-html="formattedContent"></div>
        </div>
        <div class="message-time">{{ formattedTime }}</div>
      </div>
      <div class="message-avatar">
        <AAvatar
          :size="40"
          src="/user-avatar.ico"
          class="user-avatar"
        >
          <template #icon><UserOutlined /></template>
        </AAvatar>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar as AAvatar, Button as AButton } from 'ant-design-vue'
import { RobotOutlined, UserOutlined, SoundOutlined, PauseCircleOutlined } from '@ant-design/icons-vue'
import { isTtsReady } from '../composables/useModelStatus'
import { isTtsPlaying, isTtsLoading, currentTtsMessageId, playTts, stopTts } from '../composables/useTTS'
import type { ChatMessage } from '../types'

interface Props {
  message: ChatMessage
  isLast: boolean
}

const props = defineProps<Props>()

// 判断是否为元首通讯消息
const isEmperorMessage = computed(() => {
  return props.message.content.startsWith('【元首通讯】')
})

// 处理后的内容（去掉前缀）
const displayContent = computed(() => {
  if (isEmperorMessage.value) {
    return props.message.content.replace('【元首通讯】', '')
  }
  return props.message.content
})

// 辅助函数：HTML 转义（防 XSS）
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// 辅助函数：解析 URL 和 Markdown 链接为可点击的 <a> 标签
// 使用 data-url 存储真实 URL，不使用 href 以防 Electron 窗口内跳转
// 点击后通过 shell.openExternal 在系统默认浏览器中打开
function parseLinks(text: string): string {
  // Step 1: 先转义 HTML，防止 XSS
  let result = escapeHtml(text)
  // Step 2: 解析 Markdown 链接 [text](url)
  result = result.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a class="chat-link" data-url="$2" title="点击在浏览器中打开: $2">$1</a>'
  )
  // Step 3: 解析裸 URL（不在 <a> 标签内的 https?:// 开头的 URL）
  result = result.replace(
    /(?<!data-url="|">)(https?:\/\/[^\s<>\[\]()]+)/g,
    '<a class="chat-link" data-url="$1" title="点击在浏览器中打开">$1</a>'
  )
  // Step 4: 换行符
  result = result.replace(/\n/g, '<br>')
  return result
}

const formattedContent = computed(() => {
  return parseLinks(displayContent.value)
})

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
})

// 是否正在播放当前消息
const isPlaying = computed(() => {
  return currentTtsMessageId.value === props.message.id && isTtsPlaying.value
})

// 是否正在加载TTS
const isLoadingTts = computed(() => {
  return currentTtsMessageId.value === props.message.id && isTtsLoading.value
})

// 处理链接点击：直接调用系统默认浏览器打开
function handleLinkClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (target.tagName === 'A' && target.classList.contains('chat-link')) {
    event.preventDefault()
    const url = target.getAttribute('data-url')
    if (url && window.electronAPI) {
      window.electronAPI.openExternal(url)
    }
  }
}

// 处理TTS播放/停止
function handleTtsPlay() {
  if (isPlaying.value) {
    stopTts()
  } else {
    playTts(props.message.id, props.message.content)
  }
}
</script>

<style scoped>
/* 主题修改：MessageItem 使用CSS变量 */
.message-item {
  display: flex;
  gap: var(--terran-spacing-md);
  margin-bottom: var(--terran-spacing-lg);
  animation: fadeIn 0.3s ease;
}

.message-item.message-last {
  margin-bottom: 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;
}

/* 主题修改：副官头像使用军绿色渐变 */
.assistant-avatar {
  background: linear-gradient(135deg, var(--terran-primary) 0%, var(--terran-primary-dark) 100%);
  color: #fff;
  border: 2px solid var(--terran-primary);
  box-shadow: var(--terran-glow-primary);
}

/* 元首头像样式 - 红色边框 */
.emperor-avatar {
  background: linear-gradient(135deg, #ff4d4f 0%, #a8071a 100%);
  color: #fff;
  border: 2px solid #ffd700;
  box-shadow: 0 0 10px rgba(255, 77, 79, 0.6), 0 0 20px rgba(255, 215, 0, 0.3);
}

/* 主题修改：用户头像使用深空蓝渐变 */
.user-avatar {
  background: linear-gradient(135deg, var(--terran-info) 0%, var(--terran-info-dark) 100%);
  color: #fff;
  border: 2px solid var(--terran-info);
  box-shadow: var(--terran-glow-info);
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.message-bubble {
  max-width: 80%;
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  border-radius: var(--terran-radius-xl);
  word-wrap: break-word;
  word-break: break-all;
}

/* 主题修改：用户消息样式 - 右侧深空蓝边框 */
.message-user .message-content {
  align-items: flex-end;
}

.message-user .message-bubble {
  background: var(--terran-msg-user-bg);
  color: #fff;
  border: 1px solid var(--terran-info);
  border-bottom-right-radius: var(--terran-radius-sm);
  box-shadow: var(--terran-glow-info);
}

/* 主题修改：副官消息样式 - 左侧主色粗边框+发光 */
.message-assistant .message-content {
  align-items: flex-start;
}

.message-assistant .message-bubble {
  background: var(--terran-msg-assistant-bg);
  color: var(--terran-text-primary);
  border: 1px solid var(--terran-border-primary);
  border-left: 3px solid var(--terran-primary);
  border-bottom-left-radius: var(--terran-radius-sm);
  box-shadow: var(--terran-inset-shadow);
}

/* 元首通讯消息样式 - 红色打底，金色点缀 */
.message-assistant .message-bubble.emperor-bubble {
  background: linear-gradient(135deg, rgba(255, 77, 79, 0.15) 0%, rgba(168, 7, 26, 0.1) 100%);
  color: #ffccc7;
  border: 1px solid #ffd700;
  border-left: 4px solid #ffd700;
  border-bottom-left-radius: var(--terran-radius-sm);
  box-shadow:
    0 0 15px rgba(255, 77, 79, 0.3),
    0 0 30px rgba(255, 215, 0, 0.1),
    inset 0 0 20px rgba(255, 77, 79, 0.05);
}

.message-assistant .message-bubble.emperor-bubble .message-text {
  color: #ffccc7;
  text-shadow: 0 0 2px rgba(255, 77, 79, 0.5);
}

.message-text {
  font-size: var(--terran-font-size-md);
  line-height: var(--terran-line-height-normal);
}

/* 聊天消息中的可点击链接 */
:deep(.chat-link) {
  color: #4da6ff;
  text-decoration: underline;
  cursor: pointer;
  transition: color 0.2s;
}

:deep(.chat-link:hover) {
  color: #80c4ff;
  text-decoration: underline;
}

/* 主题修改：消息时间使用次要文字色 */
.message-time {
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-tertiary);
  margin-top: var(--terran-spacing-xs);
}

.message-actions {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  margin-top: var(--terran-spacing-xs);
}

/* 主题修改：TTS按钮样式 */
.tts-btn {
  padding: 0;
  height: 20px;
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-tertiary);
  transition: color var(--terran-transition-base);
}

.tts-btn:hover {
  color: var(--terran-primary);
  text-shadow: var(--terran-text-glow-primary);
}

/* 主题修改：Ant Design 按钮深度样式覆盖 */
:deep(.ant-btn-link) {
  color: var(--terran-text-tertiary);
}

:deep(.ant-btn-link:hover) {
  color: var(--terran-primary);
}
</style>

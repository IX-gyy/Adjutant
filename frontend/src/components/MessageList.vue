<template>
  <div ref="listRef" class="message-list">
    <div v-if="!hasMessages && !isGenerating" class="empty-state">
      <!-- 主题修改：使用logo图片替代emoji，添加圆形外框 -->
      <div class="empty-icon-wrapper">
        <img src="/logo.jpg" alt="副官" class="empty-icon-img" />
      </div>
      <div class="empty-text">泰伦帝国副官已就绪</div>
      <div class="empty-hint">点击语音按钮或输入文字开始对话</div>
    </div>
    
    <template v-else>
      <MessageItem
        v-for="(message, index) in messages"
        :key="message.id"
        :message="message"
        :is-last="index === messages.length - 1 && !isGenerating"
      />
      
      <!-- 正在生成的回复 -->
      <div v-if="isGenerating" class="generating-message">
        <div class="message-avatar">
          <div class="avatar-icon assistant">副</div>
        </div>
        <div class="message-content">
          <div class="message-bubble">
            <div class="message-text">
              {{ currentResponse || '正在思考...' }}
              <span class="typing-cursor">|</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import MessageItem from './MessageItem.vue'
import type { ChatMessage } from '../types'

interface Props {
  messages: ChatMessage[]
  isGenerating: boolean
  currentResponse: string
}

const props = defineProps<Props>()

const listRef = ref<HTMLDivElement>()
const hasMessages = ref(props.messages.length > 0)

// 监听消息变化，自动滚动到底部
watch(
  () => [props.messages.length, props.currentResponse],
  () => {
    hasMessages.value = props.messages.length > 0
    nextTick(() => {
      scrollToBottom()
    }),
  { deep: true }
  }
)

function scrollToBottom() {
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}
</script>

<style scoped>
/* 主题修改：MessageList 使用CSS变量 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--terran-spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-xs);
  position: relative;
  z-index: 1;
}

/* 主题修改：空状态改为副官风格提示 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--terran-text-secondary);
}

/* 主题修改：logo图片圆形外框容器 */
.empty-icon-wrapper {
  width: 80px;
  height: 80px;
  border-radius: var(--terran-radius-circle);
  overflow: hidden;
  border: 3px solid var(--terran-primary);
  box-shadow: var(--terran-glow-primary), var(--terran-inset-shadow);
  margin-bottom: var(--terran-spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--terran-bg-tertiary);
}

/* 主题修改：logo图片样式 */
.empty-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 保留原empty-icon样式以防其他地方使用 */
.empty-icon {
  font-size: 64px;
  margin-bottom: var(--terran-spacing-lg);
  opacity: 0.6;
  filter: drop-shadow(0 0 10px var(--terran-primary-glow));
}

.empty-text {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-xl);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-primary);
  margin-bottom: var(--terran-spacing-sm);
  text-shadow: var(--terran-text-glow-primary);
  letter-spacing: 1px;
}

.empty-hint {
  font-size: var(--terran-font-size-md);
  color: var(--terran-text-tertiary);
}

/* 主题修改：生成中消息样式 */
.generating-message {
  display: flex;
  gap: var(--terran-spacing-md);
  animation: fadeIn 0.3s ease;
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
.avatar-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--terran-radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: #fff;
  background: linear-gradient(135deg, var(--terran-primary) 0%, var(--terran-primary-dark) 100%);
  border: 2px solid var(--terran-primary);
  box-shadow: var(--terran-glow-primary);
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* 主题修改：消息气泡使用军工风格 */
.message-bubble {
  max-width: 80%;
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  border-radius: var(--terran-radius-xl);
  background: var(--terran-msg-assistant-bg);
  color: var(--terran-text-primary);
  border: 1px solid var(--terran-border-primary);
  border-left: 3px solid var(--terran-primary);
  border-bottom-left-radius: var(--terran-radius-sm);
  word-wrap: break-word;
  word-break: break-all;
  box-shadow: var(--terran-inset-shadow);
}

.message-text {
  font-size: var(--terran-font-size-md);
  line-height: var(--terran-line-height-normal);
}

/* 主题修改：打字光标带呼吸动画 */
.typing-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: var(--terran-primary);
  font-weight: var(--terran-font-weight-bold);
  text-shadow: var(--terran-text-glow-primary);
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* 主题修改：滚动条样式使用CSS变量 */
.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: var(--terran-border-secondary);
  border-radius: var(--terran-radius-sm);
}

.message-list::-webkit-scrollbar-thumb:hover {
  background: var(--terran-text-tertiary);
}
</style>

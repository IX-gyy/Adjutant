<template>
  <div ref="listRef" class="message-list">
    <div v-if="!hasMessages && !isGenerating" class="empty-state">
      <div class="empty-icon">🤖</div>
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
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8c8c8c;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  font-size: 18px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: #8c8c8c;
}

.generating-message {
  display: flex;
  gap: 12px;
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

.avatar-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f0f2f5;
  color: #262626;
  border-bottom-left-radius: 4px;
  word-wrap: break-word;
  word-break: break-all;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
}

.typing-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: #52c41a;
  font-weight: bold;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* 滚动条样式 */
.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}

.message-list::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}
</style>

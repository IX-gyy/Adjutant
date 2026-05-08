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
          src="/adjutant-avatar.ico"
          class="assistant-avatar"
        >
          <template #icon><RobotOutlined /></template>
        </AAvatar>
      </div>
      <div class="message-content">
        <div class="message-bubble">
          <div class="message-text" v-html="formattedContent"></div>
        </div>
        <div class="message-actions">
          <div class="message-time">{{ formattedTime }}</div>
          <!-- TTS播放按钮 -->
          <AButton
            v-if="isTtsReady"
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
        <div class="message-bubble">
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

const formattedContent = computed(() => {
  // 简单处理换行符
  return props.message.content.replace(/\n/g, '<br>')
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
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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

.assistant-avatar {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  color: #fff;
}

.user-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #fff;
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
  word-break: break-all;
}

/* 用户消息样式 - 右侧 */
.message-user .message-content {
  align-items: flex-end;
}

.message-user .message-bubble {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

/* 副官消息样式 - 左侧 */
.message-assistant .message-content {
  align-items: flex-start;
}

.message-assistant .message-bubble {
  background: #f0f2f5;
  color: #262626;
  border-bottom-left-radius: 4px;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
}

.message-time {
  font-size: 12px;
  color: #8c8c8c;
}

.message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.tts-btn {
  padding: 0;
  height: 20px;
  font-size: 12px;
  color: #8c8c8c;
}

.tts-btn:hover {
  color: #52c41a;
}
</style>

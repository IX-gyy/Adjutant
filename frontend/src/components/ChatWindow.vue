<template>
  <div class="chat-window">
    <!-- 🆕 加载遮罩层 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-content">
        <a-spin size="large" tip="副官正在苏醒...">
          <template #indicator>
            <loading-outlined style="font-size: 48px" spin />
          </template>
        </a-spin>
        <div class="loading-text">模型加载中，请稍候</div>
      </div>
    </div>

    <!-- 正常内容（加载完成后完全可见） -->
    <StatusBar
      :wake-ready="isWakeReady"
      :transcribe-ready="isTranscribeReady"
      :llm-ready="isLlmReady"
      :tts-ready="isTtsReady"
    />

    <div class="chat-body">
      <MessageList
        :messages="messages"
        :is-generating="isGenerating"
        :current-response="currentResponse"
      />
    </div>

    <InputArea
      v-model="inputText"
      :disabled="!isTranscribeReady || isGenerating"
      :is-recording="isRecording"
      :recording-duration="recordingDuration"
      :audio-level="audioLevel"
      :is-generating="isGenerating"
      :is-transcribing="isTranscribing"
      :is-tts-playing="isTtsPlaying"
      placeholder="输入消息，或按住语音按钮说话..."
      @send="sendChatMessage"
      @start-record="startRecording"
      @stop-record="stopRecording"
      @cancel-generation="cancelChatGeneration"
      @stop-tts="stopTts"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { LoadingOutlined } from '@ant-design/icons-vue'
import StatusBar from './StatusBar.vue'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import { useChat, sendChatMessage, cancelChatGeneration, inputText, isGenerating, currentResponse, messages, isTranscribing } from '../composables/useChat'
import { useModelStatus } from '../composables/useModelStatus'  // 🆕 导入 isLoading
import { useAudioRecord, startRecording, stopRecording, isRecording, recordingDuration, audioLevel } from '../composables/useAudioRecord'
import { useBackend, setTranscribeMode } from '../composables/useBackend'
import { useTTS, isTtsPlaying, stopTts } from '../composables/useTTS'

const { isWakeReady, isTranscribeReady, isLlmReady, isTtsReady, isLoading } = useModelStatus()  // 🆕 解构 isLoading

useBackend()
useChat()
useAudioRecord()
useTTS()

onMounted(() => {
  setTranscribeMode()
})
</script>

<style scoped>
/* 主题修改：ChatWindow 主窗口深空黑渐变背景 */
.chat-window {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--terran-chat-bg);
  border-radius: var(--terran-radius-lg);
  overflow: hidden;
  box-shadow: var(--terran-shadow-elevated);
  border: 1px solid var(--terran-border-primary);
}

/* 主题修改：加载遮罩改为半透明深色背景 */
.loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 1000;
  background: var(--terran-bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.loading-content {
  text-align: center;
  color: var(--terran-text-primary);
}

/* 主题修改：加载文字使用科幻字体 */
.loading-text {
  margin-top: var(--terran-spacing-lg);
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-lg);
  letter-spacing: 2px;
  color: var(--terran-primary);
  text-shadow: var(--terran-text-glow-primary);
}

/* 主题修改：聊天区域带军工纹理渐变 */
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: var(--terran-chat-body-bg);
}

/* 主题修改：添加军工纹理效果 */
.chat-body::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(90deg, transparent 98%, rgba(82, 196, 26, 0.03) 98%),
    linear-gradient(0deg, transparent 98%, rgba(82, 196, 26, 0.03) 98%);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

/* 主题修改：Ant Design Spin 在遮罩中的样式覆盖 */
:deep(.ant-spin-text) {
  color: var(--terran-primary) !important;
  font-family: var(--terran-font-display);
  text-shadow: var(--terran-text-glow-primary);
}

:deep(.ant-spin-dot-item) {
  background: var(--terran-primary) !important;
  box-shadow: var(--terran-glow-primary);
}
</style>
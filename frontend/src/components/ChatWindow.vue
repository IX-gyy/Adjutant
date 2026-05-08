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
.chat-window {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

/* 🆕 加载遮罩样式 */
.loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.loading-content {
  text-align: center;
  color: #555;
}

.loading-text {
  margin-top: 16px;
  font-size: 16px;
  letter-spacing: 1px;
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
}
</style>
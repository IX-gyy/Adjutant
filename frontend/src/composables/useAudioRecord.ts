import { ref, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { transcribeFile } from './useBackend'
import { isTranscribing } from './useChat'

// 录音状态
export const isRecording = ref(false)
export const recordingDuration = ref(0)
export const audioLevel = ref(0)

// 内部状态
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let recordingTimer: number | null = null
let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
let microphoneStream: MediaStream | null = null
let levelInterval: number | null = null

/**
 * 开始录音
 * 录音完成后自动发送给后端进行转写
 */
export async function startRecording(): Promise<void> {
  if (isRecording.value) return

  try {
    // 请求麦克风权限
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    // 创建音频上下文用于音量检测
    audioContext = new AudioContext({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(microphoneStream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)

    // 创建 MediaRecorder
    const mimeType = MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : 'audio/ogg'

    mediaRecorder = new MediaRecorder(microphoneStream, { mimeType })
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: mimeType })
      await processAndSendAudio(audioBlob)
      cleanup()
    }

    // 开始录音
    mediaRecorder.start(100) // 每100ms收集一次数据
    isRecording.value = true
    recordingDuration.value = 0

    // 启动计时器
    recordingTimer = window.setInterval(() => {
      recordingDuration.value += 1
    }, 1000)

    // 启动音量检测
    startLevelDetection()

  } catch (error) {
    console.error('[useAudioRecord] 启动录音失败:', error)
    cleanup()
    throw error
  }
}

/**
 * 停止录音
 */
export function stopRecording(): void {
  if (!isRecording.value || !mediaRecorder) return

  if (mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }

  // 停止麦克风流
  if (microphoneStream) {
    microphoneStream.getTracks().forEach(track => track.stop())
  }

  isRecording.value = false
}

/**
 * 音量检测
 */
function startLevelDetection(): void {
  if (!analyser) return

  const dataArray = new Uint8Array(analyser.frequencyBinCount)

  levelInterval = window.setInterval(() => {
    if (!analyser) return
    analyser.getByteFrequencyData(dataArray)

    // 计算平均音量
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i]
    }
    const average = sum / dataArray.length
    audioLevel.value = Math.min(100, (average / 128) * 100)
  }, 100)
}

/**
 * 处理音频并发送给后端
 */
async function processAndSendAudio(audioBlob: Blob): Promise<void> {
  try {
    // 检查录音时长是否足够（至少1秒）
    if (recordingDuration.value < 1) {
      console.log('[useAudioRecord] 录音时间太短，忽略')
      message.warning('录音时间太短，请长按语音按钮至少1秒', 3)
      return
    }

    // 将 Blob 转换为 WAV 格式（Vosk 需要 16kHz 16bit PCM WAV）
    const wavBlob = await convertToWav(audioBlob)

    // 保存到临时文件
    const arrayBuffer = await wavBlob.arrayBuffer()
    const uint8Array = new Uint8Array(arrayBuffer)

    // 使用 Electron 的 API 保存临时文件
    const tempPath = await saveTempAudioFile(uint8Array)

    // 设置转写中状态
    isTranscribing.value = true
    console.log('[useAudioRecord] 开始转写...')

    // 发送给后端转写
    transcribeFile(tempPath)

  } catch (error) {
    console.error('[useAudioRecord] 处理音频失败:', error)
  }
}

/**
 * 将音频 Blob 转换为 WAV 格式
 */
async function convertToWav(audioBlob: Blob): Promise<Blob> {
  // 使用 AudioContext 解码音频并重新采样到 16kHz
  if (!audioContext) {
    audioContext = new AudioContext({ sampleRate: 16000 })
  }

  const arrayBuffer = await audioBlob.arrayBuffer()
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

  // 创建离线上下文进行重采样
  const offlineContext = new OfflineAudioContext(
    1, // 单声道
    audioBuffer.duration * 16000,
    16000
  )

  const source = offlineContext.createBufferSource()
  source.buffer = audioBuffer
  source.connect(offlineContext.destination)
  source.start()

  const renderedBuffer = await offlineContext.startRendering()

  // 转换为 WAV Blob
  return audioBufferToWav(renderedBuffer)
}

/**
 * 将 AudioBuffer 转换为 WAV Blob
 */
function audioBufferToWav(audioBuffer: AudioBuffer): Blob {
  const numberOfChannels = 1
  const sampleRate = audioBuffer.sampleRate
  const format = 1 // PCM
  const bitDepth = 16
  const bytesPerSample = bitDepth / 8

  const samples = audioBuffer.getChannelData(0)
  const dataLength = samples.length * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  // WAV 文件头
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, format, true)
  view.setUint16(22, numberOfChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numberOfChannels * bytesPerSample, true)
  view.setUint16(32, numberOfChannels * bytesPerSample, true)
  view.setUint16(34, bitDepth, true)
  writeString(36, 'data')
  view.setUint32(40, dataLength, true)

  // 写入音频数据（16bit PCM）
  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]))
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
    view.setInt16(offset, intSample, true)
    offset += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

/**
 * 保存临时音频文件
 * 使用 Electron 的 IPC 让主进程保存到临时目录
 */
async function saveTempAudioFile(data: Uint8Array): Promise<string> {
  // 生成临时文件名
  const timestamp = Date.now()
  const tempFileName = `temp_audio_${timestamp}.wav`

  // 使用 Electron 的 IPC 保存文件
  if (window.electronAPI?.saveTempAudio) {
    // 将 Uint8Array 转换为 ArrayBuffer 以避免类型不匹配
    const arrayBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer
    const filePath = await window.electronAPI.saveTempAudio(arrayBuffer, tempFileName)
    console.log('[useAudioRecord] 临时文件已保存:', filePath)
    return filePath
  } else {
    throw new Error('electronAPI.saveTempAudio 不可用')
  }
}

/**
 * 清理资源
 */
function cleanup(): void {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }

  if (levelInterval) {
    clearInterval(levelInterval)
    levelInterval = null
  }

  if (audioContext) {
    audioContext.close()
    audioContext = null
  }

  if (microphoneStream) {
    microphoneStream.getTracks().forEach(track => track.stop())
    microphoneStream = null
  }

  mediaRecorder = null
  analyser = null
  audioChunks = []
  audioLevel.value = 0
  recordingDuration.value = 0
  isRecording.value = false
}

/**
 * useAudioRecord Composable
 * 提供前端录音功能
 */
export function useAudioRecord() {
  onUnmounted(() => {
    if (isRecording.value) {
      stopRecording()
    }
    cleanup()
  })

  return {
    isRecording,
    recordingDuration,
    audioLevel,
    startRecording,
    stopRecording,
  }
}

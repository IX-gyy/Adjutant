<template>
  <div v-if="visible" class="loading-mask">
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <div class="loading-text">{{ text }}</div>
      <div v-if="showCancel" class="loading-actions">
        <button class="cancel-btn" @click="handleCancel">
          取消生成
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean
  text?: string
  showCancel?: boolean
}

withDefaults(defineProps<Props>(), {
  text: '正在生成回复...',
  showCancel: false
})

const emit = defineEmits<{
  cancel: []
}>()

function handleCancel() {
  emit('cancel')
}
</script>

<style scoped>
/* 主题修改：LoadingMask 深空黑背景 */
.loading-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--terran-bg-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-lg);
}

/* 主题修改：军工风格旋转指示灯 */
.loading-spinner {
  position: relative;
  width: 60px;
  height: 60px;
}

.spinner-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 3px solid transparent;
  border-top-color: var(--terran-primary);
  border-radius: var(--terran-radius-circle);
  animation: spin 1s linear infinite;
}

.spinner-ring:nth-child(1) {
  animation-duration: 1s;
  border-top-color: var(--terran-primary);
  box-shadow: 0 0 8px var(--terran-primary-glow);
}

.spinner-ring:nth-child(2) {
  width: 80%;
  height: 80%;
  top: 10%;
  left: 10%;
  border-top-color: var(--terran-info);
  animation-duration: 0.8s;
  animation-direction: reverse;
  box-shadow: 0 0 6px var(--terran-info-glow);
}

.spinner-ring:nth-child(3) {
  width: 60%;
  height: 60%;
  top: 20%;
  left: 20%;
  border-top-color: var(--terran-danger);
  animation-duration: 0.6s;
  box-shadow: 0 0 4px var(--terran-danger-glow);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 主题修改：加载文字使用科幻字体 */
.loading-text {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-md);
  color: var(--terran-text-secondary);
  text-align: center;
  letter-spacing: 1px;
}

.loading-actions {
  margin-top: var(--terran-spacing-sm);
}

/* 主题修改：取消按钮使用帝国暗红色 */
.cancel-btn {
  padding: var(--terran-spacing-sm) var(--terran-spacing-xl);
  border: 1px solid var(--terran-danger);
  background: transparent;
  color: var(--terran-danger);
  border-radius: 20px;
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  transition: all var(--terran-transition-base);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.cancel-btn:hover {
  background: var(--terran-danger);
  color: #fff;
  box-shadow: var(--terran-glow-danger);
}
</style>

<template>
  <div class="app">
    <ChatWindow />
  </div>
</template>

<script setup lang="ts">
import ChatWindow from './components/ChatWindow.vue'
import './styles/main.css'
</script>

<style>
/* 主题修改：移除硬编码样式，统一使用CSS变量 */
/* 全局样式已迁移至 styles/global.css */

.app {
  width: 100%;
  height: 100%;
  background: transparent;
}
</style>

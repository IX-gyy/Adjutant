import {
  app,
  BrowserWindow,
  ipcMain,
  Tray,
  Menu,
  nativeImage,
  shell,
} from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'
import fs from 'fs'

// ================= 全局变量 =================
let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let backendProcess: ChildProcess | null = null
let isQuitting = false
let isIpcSetup = false

// ================= 后端路径解析（PyInstaller打包） =================
function getBackendPath(): string {
  const isDev = !app.isPackaged
  // PyInstaller打包后的backend.exe位于frontend/backend目录下
  const backendPath = isDev
    ? path.join(process.cwd(), 'backend', 'backend.exe')
    : path.join(process.resourcesPath, 'backend', 'backend.exe')

  return backendPath
}

// ================= 后端进程管理 =================
function startBackend() {
  if (backendProcess) {
    console.log('[Main] 后端进程已存在，跳过启动')
    return
  }

  const backendPath = getBackendPath()

  if (!fs.existsSync(backendPath)) {
    console.error('[Main] 后端可执行文件不存在:', backendPath)
    return
  }

  console.log('[Main] 启动后端:', backendPath)

  backendProcess = spawn(backendPath, [], {
    cwd: path.dirname(backendPath), // 工作目录设为 backend 文件夹
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true
  })

  // 接收后端 stdout 的 JSON 事件，转发给渲染进程
  let buffer = ''
  backendProcess.stdout?.on('data', (data: Buffer) => {
    buffer += data.toString('utf8')
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        const event = JSON.parse(trimmed)
        console.log('[Main] 后端事件:', event)
        if (event.event === 'wake') {
          showMainWindow()
        }
        mainWindow?.webContents.send('from-backend', event)
      } catch {
        console.log('[Main] 后端输出:', trimmed)
      }
    }
  })

  backendProcess.stderr?.on('data', (data: Buffer) => {
    const msg = data.toString('utf8').trim()
    // 过滤正常的日志信息，只标记真正的错误
    if (msg.includes('错误') || msg.includes('失败') || msg.includes('Error') || msg.includes('Exception')) {
      console.error('[Main] 后端错误:', msg)
    } else {
      console.log('[Main] 后端日志:', msg)
    }
  })

  backendProcess.on('close', (code) => {
    console.log(`[Main] 后端进程退出，退出码: ${code}`)
    backendProcess = null
  })

  backendProcess.on('error', (err) => {
    console.error('[Main] 后端进程启动失败:', err)
    backendProcess = null // 释放引用
  })
}

function stopBackend() {
  if (backendProcess) {
    console.log('[Main] 终止后端进程')
    backendProcess.kill()
    backendProcess = null
  }
}

function sendToBackend(action: Record<string, unknown>) {
  console.log('[Main] sendToBackend 检查: backendProcess=', !!backendProcess,
    'stdin=', !!(backendProcess?.stdin),
    'destroyed=', backendProcess?.stdin?.destroyed)
  if (backendProcess && backendProcess.stdin && !backendProcess.stdin.destroyed) {
    const line = JSON.stringify(action) + '\n'
    const result = backendProcess.stdin.write(line, 'utf-8')
    if (!result) {
      console.log('[Main] 写入缓冲区已满，等待 drain 事件')
      backendProcess.stdin.once('drain', () => {
        console.log('[Main] 缓冲区已清空')
      })
    }
    console.log('[Main] 发送指令到后端:', action, '写入结果:', result)
  } else {
    console.warn('[Main] 后端进程未就绪，无法发送指令')
  }
}

// ================= 窗口管理 =================
function createWindow() {
  if (mainWindow) {
    console.log('[Main] 窗口已存在，跳过创建')
    return mainWindow
  }

  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: '#1a1a2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    icon: path.join(__dirname, '..', 'public', 'icon.ico'),
  })

  const isDev = !app.isPackaged
  if (isDev) {
    const loadDevURL = async () => {
      const maxRetries = 30
      const retryDelay = 500
      for (let i = 0; i < maxRetries; i++) {
        try {
          await mainWindow?.loadURL('http://localhost:5173')
          console.log('[Main] 开发服务器加载成功')
          return
        } catch (err) {
          console.log(`[Main] 等待开发服务器... (${i + 1}/${maxRetries})`)
          await new Promise(resolve => setTimeout(resolve, retryDelay))
        }
      }
      console.error('[Main] 无法连接到开发服务器')
    }
    loadDevURL()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
    mainWindow?.focus()
  })

  mainWindow.on('minimize', () => {
    console.log('[Main] 窗口最小化')
  })

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      console.log('[Main] 窗口关闭按钮被点击，隐藏到托盘')
      hideMainWindow()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  return mainWindow
}

function showMainWindow() {
  if (mainWindow) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore()
    }
    mainWindow.show()
    mainWindow.focus()
    sendToBackend({ action: 'set_mode', mode: 'transcribe' })
  }
}

function hideMainWindow() {
  if (mainWindow) {
    mainWindow.hide()
    sendToBackend({ action: 'set_mode', mode: 'wake' })
  }
}

function minimizeWindow() {
  if (mainWindow) {
    mainWindow.minimize()
  }
}

function quitApp() {
  isQuitting = true
  stopBackend()
  if (tray) {
    tray.destroy()
    tray = null
  }
  app.quit()
}

// ================= 托盘管理 =================
function createTray() {
  if (tray) {
    console.log('[Main] 托盘已存在，跳过创建')
    return
  }

  const iconPath = path.join(__dirname, '..', 'public', 'cube.ico')
  const trayIcon = nativeImage.createFromPath(iconPath)

  tray = new Tray(trayIcon)

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => { showMainWindow() },
    },
    {
      label: '隐藏主窗口',
      click: () => { hideMainWindow() },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => { quitApp() },
    },
  ])

  tray.setToolTip('副官AI')
  tray.setContextMenu(contextMenu)

  tray.on('click', () => { showMainWindow() })
  tray.on('double-click', () => { showMainWindow() })
}

// ================= IPC 通信 =================
function setupIpc() {
  if (isIpcSetup) {
    console.log('[Main] IPC 已设置，跳过')
    return
  }

  console.log('[Main] 设置 IPC 通信')

  ipcMain.on('to-backend', (_event, action: Record<string, unknown>) => {
    sendToBackend(action)
  })

  ipcMain.on('show-window', () => { showMainWindow() })
  ipcMain.on('hide-window', () => { hideMainWindow() })
  ipcMain.on('minimize-window', () => { minimizeWindow() })

  // 获取后端路径（调试用）
  ipcMain.handle('get-backend-path', () => {
    return getBackendPath()
  })

  ipcMain.handle('save-temp-audio', (_event, data: ArrayBuffer, fileName: string) => {
    try {
      const tempDir = path.join(app.getPath('temp'), 'adjutant-audio')
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true })
      }
      const filePath = path.join(tempDir, fileName)
      fs.writeFileSync(filePath, Buffer.from(data))
      console.log('[Main] 临时音频文件已保存:', filePath)
      return filePath
    } catch (error) {
      console.error('[Main] 保存临时音频文件失败:', error)
      throw error
    }
  })

  ipcMain.on('open-external', (_event, url: string) => {
    shell.openExternal(url)
  })

  isIpcSetup = true
}

// ================= 应用生命周期 =================
app.whenReady().then(() => {
  createWindow()
  createTray()
  setupIpc()
  startBackend()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else {
      showMainWindow()
    }
  })
})

app.on('window-all-closed', () => {
  // 保持后台运行
})

app.on('before-quit', () => {
  isQuitting = true
})

app.on('will-quit', () => {
  stopBackend()
})
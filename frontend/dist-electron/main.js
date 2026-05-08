//#region \0rolldown/runtime.js
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
	if (from && typeof from === "object" || typeof from === "function") for (var keys = __getOwnPropNames(from), i = 0, n = keys.length, key; i < n; i++) {
		key = keys[i];
		if (!__hasOwnProp.call(to, key) && key !== except) __defProp(to, key, {
			get: ((k) => from[k]).bind(null, key),
			enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable
		});
	}
	return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", {
	value: mod,
	enumerable: true
}) : target, mod));
//#endregion
let electron = require("electron");
let path = require("path");
path = __toESM(path);
let child_process = require("child_process");
let fs = require("fs");
fs = __toESM(fs);
//#region electron/main.ts
var mainWindow = null;
var tray = null;
var backendProcess = null;
var isQuitting = false;
var isIpcSetup = false;
function getBackendPath() {
	return !electron.app.isPackaged ? path.default.join(process.cwd(), "backend", "backend.exe") : path.default.join(process.resourcesPath, "backend", "backend.exe");
}
function startBackend() {
	if (backendProcess) {
		console.log("[Main] 后端进程已存在，跳过启动");
		return;
	}
	const backendPath = getBackendPath();
	if (!fs.default.existsSync(backendPath)) {
		console.error("[Main] 后端可执行文件不存在:", backendPath);
		return;
	}
	console.log("[Main] 启动后端:", backendPath);
	backendProcess = (0, child_process.spawn)(backendPath, [], {
		cwd: path.default.dirname(backendPath),
		stdio: [
			"pipe",
			"pipe",
			"pipe"
		],
		windowsHide: true
	});
	let buffer = "";
	backendProcess.stdout?.on("data", (data) => {
		buffer += data.toString("utf8");
		const lines = buffer.split("\n");
		buffer = lines.pop() || "";
		for (const line of lines) {
			const trimmed = line.trim();
			if (!trimmed) continue;
			try {
				const event = JSON.parse(trimmed);
				console.log("[Main] 后端事件:", event);
				if (event.event === "wake") showMainWindow();
				mainWindow?.webContents.send("from-backend", event);
			} catch {
				console.log("[Main] 后端输出:", trimmed);
			}
		}
	});
	backendProcess.stderr?.on("data", (data) => {
		const msg = data.toString("utf8").trim();
		if (msg.includes("错误") || msg.includes("失败") || msg.includes("Error") || msg.includes("Exception")) console.error("[Main] 后端错误:", msg);
		else console.log("[Main] 后端日志:", msg);
	});
	backendProcess.on("close", (code) => {
		console.log(`[Main] 后端进程退出，退出码: ${code}`);
		backendProcess = null;
	});
	backendProcess.on("error", (err) => {
		console.error("[Main] 后端进程启动失败:", err);
		backendProcess = null;
	});
}
function stopBackend() {
	if (backendProcess) {
		console.log("[Main] 终止后端进程");
		backendProcess.kill();
		backendProcess = null;
	}
}
function sendToBackend(action) {
	console.log("[Main] sendToBackend 检查: backendProcess=", !!backendProcess, "stdin=", !!backendProcess?.stdin, "destroyed=", backendProcess?.stdin?.destroyed);
	if (backendProcess && backendProcess.stdin && !backendProcess.stdin.destroyed) {
		const line = JSON.stringify(action) + "\n";
		const result = backendProcess.stdin.write(line, "utf-8");
		if (!result) {
			console.log("[Main] 写入缓冲区已满，等待 drain 事件");
			backendProcess.stdin.once("drain", () => {
				console.log("[Main] 缓冲区已清空");
			});
		}
		console.log("[Main] 发送指令到后端:", action, "写入结果:", result);
	} else console.warn("[Main] 后端进程未就绪，无法发送指令");
}
function createWindow() {
	if (mainWindow) {
		console.log("[Main] 窗口已存在，跳过创建");
		return mainWindow;
	}
	mainWindow = new electron.BrowserWindow({
		width: 900,
		height: 700,
		show: false,
		frame: false,
		transparent: true,
		backgroundColor: "#1a1a2e",
		webPreferences: {
			preload: path.default.join(__dirname, "preload.js"),
			contextIsolation: true,
			nodeIntegration: false,
			sandbox: false
		},
		icon: path.default.join(__dirname, "..", "public", "icon.ico")
	});
	if (!electron.app.isPackaged) {
		const loadDevURL = async () => {
			const maxRetries = 30;
			const retryDelay = 500;
			for (let i = 0; i < maxRetries; i++) try {
				await mainWindow?.loadURL("http://localhost:5173");
				console.log("[Main] 开发服务器加载成功");
				return;
			} catch (err) {
				console.log(`[Main] 等待开发服务器... (${i + 1}/${maxRetries})`);
				await new Promise((resolve) => setTimeout(resolve, retryDelay));
			}
			console.error("[Main] 无法连接到开发服务器");
		};
		loadDevURL();
	} else mainWindow.loadFile(path.default.join(__dirname, "..", "dist", "index.html"));
	mainWindow.once("ready-to-show", () => {
		mainWindow?.show();
		mainWindow?.focus();
	});
	mainWindow.on("minimize", () => {
		console.log("[Main] 窗口最小化");
	});
	mainWindow.on("close", (event) => {
		if (!isQuitting) {
			event.preventDefault();
			console.log("[Main] 窗口关闭按钮被点击，隐藏到托盘");
			hideMainWindow();
		}
	});
	mainWindow.on("closed", () => {
		mainWindow = null;
	});
	return mainWindow;
}
function showMainWindow() {
	if (mainWindow) {
		if (mainWindow.isMinimized()) mainWindow.restore();
		mainWindow.show();
		mainWindow.focus();
		sendToBackend({
			action: "set_mode",
			mode: "transcribe"
		});
	}
}
function hideMainWindow() {
	if (mainWindow) {
		mainWindow.hide();
		sendToBackend({
			action: "set_mode",
			mode: "wake"
		});
	}
}
function minimizeWindow() {
	if (mainWindow) mainWindow.minimize();
}
function quitApp() {
	isQuitting = true;
	stopBackend();
	if (tray) {
		tray.destroy();
		tray = null;
	}
	electron.app.quit();
}
function createTray() {
	if (tray) {
		console.log("[Main] 托盘已存在，跳过创建");
		return;
	}
	const iconPath = path.default.join(__dirname, "..", "public", "cube.ico");
	tray = new electron.Tray(electron.nativeImage.createFromPath(iconPath));
	const contextMenu = electron.Menu.buildFromTemplate([
		{
			label: "显示主窗口",
			click: () => {
				showMainWindow();
			}
		},
		{
			label: "隐藏主窗口",
			click: () => {
				hideMainWindow();
			}
		},
		{ type: "separator" },
		{
			label: "退出",
			click: () => {
				quitApp();
			}
		}
	]);
	tray.setToolTip("副官AI");
	tray.setContextMenu(contextMenu);
	tray.on("click", () => {
		showMainWindow();
	});
	tray.on("double-click", () => {
		showMainWindow();
	});
}
function setupIpc() {
	if (isIpcSetup) {
		console.log("[Main] IPC 已设置，跳过");
		return;
	}
	console.log("[Main] 设置 IPC 通信");
	electron.ipcMain.on("to-backend", (_event, action) => {
		sendToBackend(action);
	});
	electron.ipcMain.on("show-window", () => {
		showMainWindow();
	});
	electron.ipcMain.on("hide-window", () => {
		hideMainWindow();
	});
	electron.ipcMain.on("minimize-window", () => {
		minimizeWindow();
	});
	electron.ipcMain.handle("get-backend-path", () => {
		return getBackendPath();
	});
	electron.ipcMain.handle("save-temp-audio", (_event, data, fileName) => {
		try {
			const tempDir = path.default.join(electron.app.getPath("temp"), "adjutant-audio");
			if (!fs.default.existsSync(tempDir)) fs.default.mkdirSync(tempDir, { recursive: true });
			const filePath = path.default.join(tempDir, fileName);
			fs.default.writeFileSync(filePath, Buffer.from(data));
			console.log("[Main] 临时音频文件已保存:", filePath);
			return filePath;
		} catch (error) {
			console.error("[Main] 保存临时音频文件失败:", error);
			throw error;
		}
	});
	electron.ipcMain.on("open-external", (_event, url) => {
		electron.shell.openExternal(url);
	});
	isIpcSetup = true;
}
electron.app.whenReady().then(() => {
	createWindow();
	createTray();
	setupIpc();
	startBackend();
	electron.app.on("activate", () => {
		if (electron.BrowserWindow.getAllWindows().length === 0) createWindow();
		else showMainWindow();
	});
});
electron.app.on("window-all-closed", () => {});
electron.app.on("before-quit", () => {
	isQuitting = true;
});
electron.app.on("will-quit", () => {
	stopBackend();
});
//#endregion

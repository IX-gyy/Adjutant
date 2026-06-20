let electron = require("electron");
//#region electron/preload.ts
electron.contextBridge.exposeInMainWorld("electronAPI", {
	sendToBackend: (action) => {
		electron.ipcRenderer.send("to-backend", action);
	},
	onBackendEvent: (callback) => {
		const handler = (_, data) => callback(data);
		electron.ipcRenderer.on("from-backend", handler);
		return () => {
			electron.ipcRenderer.removeListener("from-backend", handler);
		};
	},
	onceBackendEvent: (callback) => {
		const handler = (_, data) => callback(data);
		electron.ipcRenderer.once("from-backend", handler);
	},
	showWindow: () => electron.ipcRenderer.send("show-window"),
	hideWindow: () => electron.ipcRenderer.send("hide-window"),
	minimizeWindow: () => electron.ipcRenderer.send("minimize-window"),
	getBackendPath: () => electron.ipcRenderer.invoke("get-backend-path"),
	saveTempAudio: (data, fileName) => electron.ipcRenderer.invoke("save-temp-audio", data, fileName),
	openExternal: (url) => electron.ipcRenderer.send("open-external", url)
});
//#endregion

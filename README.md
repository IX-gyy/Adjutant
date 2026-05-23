# AI阿塔尼斯项目——帝国副官语音助手
## 技术栈
前端：
- Vue3
- TypeScript
- Electron

在frontend文件夹下使用`npm install`来安装相关依赖  

后端：
- python3.10
- vosk
- llama-cpp-python
- onnx runtime
- pyinstaller

建议在conda虚拟空间中安装相关依赖

## 下载模型
你需要在backend文件夹下创建models文件夹，下面存放3个模型：
- qwen2.5-3b-it-Q4_K_M-LOT.gguf[下载](https://www.modelscope.cn/models/okwinds/Qwen2.5-3B-Instruct-GGUF-V3-LOT/files)
- vosk-model-small-cn[下载](https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip)
- kokoro-zh onnx版本 参考[GitHub网页](https://github.com/thewh1teagle/kokoro-onnx/blob/main/examples/chinese.py)

最终你的文件夹结构应该如下：
```
kokoro-zh/
qwen2.5-3b-it-Q4_K_M-LOT.gguf
vosk-model-small-cn/
```

## 后端依赖
建议直接打开backend.py，一个一个看还有哪个依赖库没安装，这里不赘述了

## 模型API
项目的赫尔墨斯记忆架构使用了[智谱API](https://bigmodel.cn/)  
天气查询使用了[和风天气API](https://console.qweather.com/home?lang=zh)  
你需要先注册，在网站上取得自己的api key后（它们都有免费额度，不必担心），在应用启动后打开设置填入，记忆和天气查询功能才可以使用

## 项目启动
你需要先在backend文件夹下使用pyinstaller将后端打包成多文件结构，命令为：`pyinstaller backend.spec`  
打包完毕后会生成一个dist文件夹和一个build文件夹，将dist文件夹中的backend文件夹整个复制到frontend中作为项目的后端  
在frontend文件夹下输入`npm run electron:dev`即可运行  
如果要最终打包，则输入`npm run electron:build`，注意TS的build较严格，你需要检查你的代码中任何warning，全部消除后才可以打包  

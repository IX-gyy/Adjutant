# AI阿塔尼斯项目——帝国副官语音助手

## ⚖️ 法律声明 / Legal Disclaimer

**本项目是一个粉丝创作的、非商业性质的个人学习项目。**

- 本项目的人设、术语及部分音频素材的灵感来源于暴雪娱乐（Blizzard Entertainment, Inc.）旗下的《星际争霸》（StarCraft）系列游戏。所有相关商标、版权、角色、语音及世界观均归暴雪娱乐 / 动视暴雪（Activision Blizzard） / 微软（Microsoft）及其关联方所有。
- 本项目中的彩蛋音频片段来源于《星际争霸2》游戏，属于已公开发布内容的极小部分引用（单段不超过 30 秒），仅为粉丝致敬目的，不构成对原作的替代或商业利用。我们相信此类使用符合合理使用 / 合理引用原则。
- 本项目**不隶属于、未获得暴雪娱乐、动视暴雪或微软的认可或赞助**。项目中的任何内容均不代表上述公司的官方立场。
- 本项目**完全开源、不涉及任何商业盈利**，所有代码仅供学习和研究使用。项目维护者不会因本项目获得任何直接或间接的经济收益。
- 若您是相关权利人且认为本项目中的某些内容侵犯了您的合法权益，请通过本项目的 GitHub Issues 或仓库联系方式与我们取得联系，我们将在收到通知后及时处理。

若您使用本项目的代码或运行本项目，即表示您知悉并同意：
- 本项目仅供个人在本地设备上使用，不得用于任何商业目的或对外公开传播；
- 本项目中的彩蛋音频文件仅能在您已合法拥有《星际争霸2》游戏的前提下使用；
- 使用者应自行遵守所在地法律法规及相关平台服务条款；
- **本项目的 AI 对话、记忆提取、语音合成等功能均基于第三方大语言模型（LLM）和机器学习模型生成，其输出内容不代表本项目维护者的观点或立场；**
- **AI 生成内容可能存在事实错误、偏见或不当表述，使用者应自行甄别判断。本项目维护者不对任何 AI 生成内容承担法律责任。**

---

**This is a fan-made, non-commercial, personal learning project.**

- The persona, terminology, and some audio materials in this project are inspired by the *StarCraft* series created by Blizzard Entertainment, Inc. All related trademarks, copyrights, characters, voice lines, and world-building elements are the property of Blizzard Entertainment / Activision Blizzard / Microsoft and their affiliates.
- The easter egg audio clips in this project are sourced from *StarCraft II* and constitute de minimis excerpts (under 30 seconds each) of publicly released content, used solely for fan tribute purposes. We believe such use falls within fair use / fair dealing principles.
- This project is **not affiliated with, endorsed by, or sponsored by** Blizzard Entertainment, Activision Blizzard, or Microsoft. Nothing in this project represents the official stance of these companies.
- This project is **fully open-source and completely non-commercial**. All code is provided for educational and research purposes only. The project maintainer receives no financial benefit, direct or indirect, from this project.
- If you are a rights holder and believe any content in this project infringes upon your rights, please contact us via GitHub Issues or the repository contact information. We will respond promptly upon notification.

By using the code or running this project, you acknowledge and agree that:
- This project is for personal, local use only and must not be used for any commercial purpose or public distribution;
- The easter egg audio files in this project may only be used if you legally own *StarCraft II*;
- You are responsible for complying with applicable laws, regulations, and platform terms of service;
- **The AI dialogue, memory extraction, speech synthesis, and other features in this project are powered by third-party large language models (LLMs) and machine learning models. Their outputs do not represent the views or opinions of the project maintainer;**
- **AI-generated content may contain factual errors, biases, or inappropriate statements. Users should exercise their own judgment in evaluating such content. The project maintainer assumes no legal liability for any AI-generated output.**

---

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
- bge-small-zh-v1.5[下载](https://www.modelscope.cn/models/fuyuantech/bge-small-q8-zh-v1.5)

最终你的文件夹结构应该如下：
```
kokoro-zh/
qwen2.5-3b-it-Q4_K_M-LOT.gguf
bge-small-q8-zh-v1.5.gguf
vosk-model-small-cn/
```

## 后端依赖
建议直接打开backend.py，一个一个看还有哪个依赖库没安装，这里不赘述了

## 模型API
项目的赫尔墨斯记忆架构使用了[智谱API](https://bigmodel.cn/)  
天气查询使用了[和风天气API](https://console.qweather.com/home?lang=zh)  
网络搜索使用了[百度千帆API](https://cloud.baidu.com/doc/qianfan/s/Omh4su4s0)
你需要先注册，在网站上取得自己的api key后（它们都有免费额度，不必担心），在应用启动后打开设置填入，记忆、天气查询、网络搜索功能才可以使用

## 项目启动
你需要先在backend文件夹下使用pyinstaller将后端打包成多文件结构，命令为：`pyinstaller backend.spec`  
打包完毕后会生成一个dist文件夹和一个build文件夹，将dist文件夹中的backend文件夹整个复制到frontend中作为项目的后端  
在frontend文件夹下输入`npm run electron:dev`即可运行  
如果要最终打包，则输入`npm run electron:build`，注意TS的build较严格，你需要检查你的代码中任何warning，全部消除后才可以打包  

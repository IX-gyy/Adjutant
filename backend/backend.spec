# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ────────────────── 动态获取关键库路径（原有逻辑）──────────────────
# 获取 llama_cpp 库路径
try:
    import llama_cpp
    LLAMA_CPP_PATH = os.path.dirname(llama_cpp.__file__)
except ImportError:
    print("错误：未找到 llama_cpp 库，请先安装依赖", file=sys.stderr)
    sys.exit(1)

# 获取 vosk 库路径（自动适配当前 conda/venv 环境）
try:
    import vosk
    VOSK_LIB_PATH = os.path.dirname(vosk.__file__)
except ImportError:
    print("错误：未找到 vosk 库，请先安装依赖", file=sys.stderr)
    sys.exit(1)

# 当前 spec 文件所在目录（通常就是 backend 目录）
spec_dir = os.path.dirname(os.path.abspath(SPEC))
block_cipher = None

# ────────────────── 1. 数据文件打包 ──────────────────
# 需要内置数据文件的第三方包（TTS 相关）
packages_with_data = [
    'kokoro_onnx',
    'misaki',
    'language_tags',
    'csvw',
    'segments',
    'espeakng_loader',
    'chromadb',
    'openai',
    'pydantic',
    'httpx',
]

all_datas = []

# 原有模型文件夹
all_datas.append((os.path.join(spec_dir, 'models'), 'models'))

# 彩蛋系统新增：规则配置目录
all_datas.append((os.path.join(spec_dir, 'config'), 'config'))
# 彩蛋系统新增：音频资源目录（注意拼写为 assets）
all_datas.append((os.path.join(spec_dir, 'assets'), 'assets'))
# MCP统一工具链：非代码资源文件（prompts下的txt模板）
all_datas.append((os.path.join(spec_dir, 'mcp', 'prompts'), 'mcp/prompts'))

# 收集以上第三方包的数据文件
for pkg in packages_with_data:
    try:
        all_datas.extend(collect_data_files(pkg))
    except Exception:
        pass

# 原有 vosk 完整库打包
all_datas.append((VOSK_LIB_PATH, 'vosk'))

# 原有 llama_cpp 的 lib 目录打包
all_datas.append((os.path.join(LLAMA_CPP_PATH, 'lib'), 'llama_cpp/lib'))

# ────────────────── 2. 二进制文件打包（动态库）──────────────────
binaries = [
    # llama_cpp 的 dll 文件（Windows）
    (os.path.join(LLAMA_CPP_PATH, 'lib', '*.dll'), 'llama_cpp/lib'),
    # vosk 的 dll 文件（Windows）
    (os.path.join(VOSK_LIB_PATH, '*.dll'), 'vosk'),
]

# ────────────────── 3. 隐藏导入（全量覆盖）──────────────────
hiddenimports = [
    # Vosk 相关
    'vosk',
    'sounddevice',
    'pypinyin',

    # Llama.cpp 相关
    'llama_cpp',
    'llama_cpp.llama',
    'llama_cpp._ctypes_extensions',

    # NumPy 通用
    'numpy',
    'numpy.core._multiarray_umath',

    # TTS 新增相关
    'misaki',
    'kokoro_onnx',
    'language_tags',
    'csvw',
    'segments',
    'espeakng_loader',
    'json',
    'email.mime.text',
    'email.mime.multipart',
]

# 追加：ChromaDB 全量子模块（含 hnsw 向量索引、sqlite 元数据存储等 C 扩展）
hiddenimports.extend(collect_submodules('chromadb'))

# 追加：OpenAI 全量子模块（含 chat.completions、types、base_client 等）
hiddenimports.extend(collect_submodules('openai'))

# 追加：MCP统一工具链模块
hiddenimports.extend([
    'mcp',
    'mcp.mcp_manager',
    'mcp.keyword_filter',
    'mcp.tools',
    'mcp.tools.todo_tool',
    'mcp.tools.weather_tool',
    'mcp.tools.system_tool',
    'mcp.tools.time_tool',
])

# 追加：psutil（系统状态查询依赖）
hiddenimports.extend(collect_submodules('psutil'))

# 建议追加：Pydantic（openai 强依赖，部分版本 PyInstaller 会漏）
hiddenimports.extend(collect_submodules('pydantic'))

# 建议追加：httpx（openai 底层 HTTP 客户端）
hiddenimports.extend(collect_submodules('httpx'))

# ────────────────── 4. PyInstaller 分析配置 ──────────────────
a = Analysis(
    ['backend.py'],
    pathex=[spec_dir],
    binaries=binaries,
    datas=all_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # 开发阶段保留控制台；正式交付可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
"""
检查 PyInstaller 对关键库的 hook 支持情况
用法: conda activate vosk_env && python _check_hooks.py
"""
import os
import sys

# 1. 找到 PyInstaller 自带的 hooks 目录
import PyInstaller
builtin_hooks = os.path.join(os.path.dirname(PyInstaller.__file__), 'hooks')
print(f"PyInstaller 内置 hooks 目录: {builtin_hooks}")
print()

# 2. 检查是否有 hooks-contrib 包
try:
    import PyInstaller.hooks as hooks_pkg
    contrib_hooks = os.path.join(os.path.dirname(hooks_pkg.__file__), 'hooks')
    print(f"hooks-contrib 目录: {contrib_hooks}")
except Exception:
    contrib_hooks = None
    print("未安装 pyinstaller-hooks-contrib")
print()

# 3. 搜索所有相关 hook 文件
all_hooks_dirs = [builtin_hooks]
if contrib_hooks:
    all_hooks_dirs.append(contrib_hooks)

keywords = ['torch', 'transform', 'sentence', 'tokenizer', 'numpy', 'huggingface', 'bert']

for hooks_dir in all_hooks_dirs:
    if not os.path.isdir(hooks_dir):
        continue
    print(f"=== {hooks_dir} ===")
    for kw in keywords:
        matches = sorted([f for f in os.listdir(hooks_dir) if kw in f.lower()])
        if matches:
            for m in matches:
                print(f"  {m}")
        else:
            print(f"  [{kw}] 无匹配")
    print()

# 4. 验证关键库能否正常 import
print("=== 关键库 import 验证 ===")
libs = [
    'sentence_transformers',
    'transformers',
    'transformers.models.bert',
    'transformers.models.bert.modeling_bert',
    'transformers.models.bert.tokenization_bert',
    'transformers.models.bert.configuration_bert',
    'tokenizers',
    'torch',
    'torch.nn',
    'numpy',
    'huggingface_hub',
]
for lib in libs:
    try:
        __import__(lib)
        print(f"  ✓ {lib}")
    except Exception as e:
        print(f"  ✗ {lib} — {e}")

# 5. 查看 transformers 的 hidden imports hook（如果有的话）
print()
for hooks_dir in all_hooks_dirs:
    hook_file = os.path.join(hooks_dir, 'hook-transformers.py')
    if os.path.isfile(hook_file):
        print(f"=== {hook_file} 内容摘要 ===")
        with open(hook_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # 只打印关键行
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                print(f"  {stripped}")
        break
else:
    print("未找到 hook-transformers.py")

print()
print("=== 检查完成 ===")

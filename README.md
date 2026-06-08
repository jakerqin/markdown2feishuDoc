# Markdown 到飞书自动同步工具

把本地 Markdown 目录单向同步到飞书云文档。工具会递归扫描 `.md` 文件，保留本地目录结构，只上传新增或内容变化的文件，并支持通过 macOS `launchd` 每天定时执行。

> 当前同步方向是 **本地 Markdown -> 飞书云文档**。不支持把飞书文档修改自动回写到本地。

## 功能特性

- 递归扫描本地 Markdown 目录，支持 iCloud Drive 路径。
- 支持通过 `sync_targets.json` 配置多组“本地目录 -> 飞书文件夹”映射。
- 自动规范化 `.env` 中带反斜杠的终端路径。
- 按本地目录结构在飞书中创建或复用文件夹。
- 将 Markdown 导入为飞书新版云文档。
- 识别 Markdown 中的本地图片，上传并替换飞书文档中的图片块。
- 使用 `.sync_state.json` 记录同步状态，只上传新增或内容变化的 Markdown。
- 记录飞书文件夹 token，避免重复创建同名文件夹。
- 记录飞书文档 token，文件变化后上传新版本并删除旧文档，减少重复文档。
- 检测 iCloud `.icloud` 占位文件，提示先下载到本机。
- 支持 `--mark-current-synced` 建立同步基线。
- 支持通过 Terminal + `launchd` 每天凌晨 5 点自动同步，规避后台进程读取 iCloud Drive 的 macOS 权限问题。

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 创建飞书自建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app) 创建企业自建应用。
2. 在「权限管理」中添加云文档和云空间相关权限，例如：
   - `drive:drive:readonly`
   - `drive:drive:write`
   - `drive:drive`
   - `drive:file`
   - `drive:file:upload`
   - `docx:document`
   - `docx:document:readonly`
3. 获取应用的 App ID 和 App Secret。

### 3. 授权目标飞书文件夹

按照 [飞书官方说明](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-add-permissions-to-app) 给自建应用添加目标文件夹权限：

1. 打开飞书云文档中的目标文件夹。
2. 点击「...」->「设置」->「成员管理」。
3. 添加你的自建应用。

文件夹 URL 最后一段就是 folder token：

```text
https://xxx.feishu.cn/drive/folder/xxxxxxxxxxxxx
                                    ^
                               folder_token
```

![获取文件夹 Token 示例](img/image.png)

### 4. 配置环境变量

复制示例环境变量文件，并按自己的飞书应用信息修改 `.env`：

```bash
cp .env.example .env
```

`.env.example` 示例：

```bash
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
SYNC_TARGETS_CONFIG=sync_targets.json
```

`SYNC_TARGETS_CONFIG` 可省略，默认读取项目根目录的 `sync_targets.json`。

### 5. 配置同步目标

复制示例文件：

```bash
cp sync_targets.example.json sync_targets.json
```

编辑 `sync_targets.json`，配置一组或多组本地目录与飞书文件夹的一一对应关系：

```json
{
  "targets": [
    {
      "id": "research",
      "local_dir": "/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/researchspace",
      "feishu_folder_token": "your_research_folder_token"
    },
    {
      "id": "work",
      "local_dir": "/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/worknotes",
      "feishu_folder_token": "your_work_folder_token"
    }
  ]
}
```

字段说明：

- `id`：同步目标唯一标识，用于隔离 `.sync_state.json` 中的文件状态。不同目标不能重复。
- `local_dir`：本地 Markdown 根目录。
- `feishu_folder_token`：该本地目录对应的飞书目标文件夹 token。

`sync_targets.json` 可能包含私有路径和飞书 folder token，默认已被 `.gitignore` 忽略。提交 PR 时请提交 `sync_targets.example.json`，不要提交自己的真实配置。

如果项目根目录没有 `sync_targets.json`，程序会回退到旧版 `.env` 单目标配置：

```bash
LOCAL_MARKDOWN_DIR=/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/researchspace
DEFAULT_PARENT_FOLDER_TOKEN=your_folder_token
```

如果从终端复制 iCloud 路径，可能会带反斜杠：

```text
/Users/yourname/Library/Mobile\ Documents/com\~apple\~CloudDocs/researchspace
```

程序会自动规范化为 Python 可读取的路径：

```text
/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/researchspace
```

### 6. 手动同步

```bash
python3 main.py
```

首次启用定时同步前，如果当前飞书里已经有对应文档，可以先只记录当前文件状态，不上传：

```bash
python3 main.py --mark-current-synced
```

之后再次运行 `python3 main.py` 时，只会上传新增或内容变化的 Markdown。

## 验收步骤

配置完成后，建议按下面顺序验收，避免第一次运行时误判同步结果。

### 1. 检查 `sync_targets.json` 格式

```bash
python3 -m json.tool sync_targets.json >/tmp/sync_targets.checked.json
```

没有输出表示 JSON 格式正确。

### 2. 检查同步目标是否能被加载

```bash
python3 - <<'PY'
from src.sync_targets import load_sync_targets

targets = load_sync_targets()
print(f"targets: {len(targets)}")
for target in targets:
    print(f"- {target.id}")
    print(f"  local: {target.local_dir}")
    print(f"  feishu: {target.feishu_folder_token}")
PY
```

重点确认：

- target 数量正确。
- 每个 `id` 唯一。
- `local_dir` 路径正确，并且没有多余反斜杠。
- `feishu_folder_token` 指向预期的飞书文件夹。

### 3. 检查本地目录是否存在

```bash
python3 - <<'PY'
import os
from src.sync_targets import load_sync_targets

for target in load_sync_targets():
    ok = os.path.isdir(target.local_dir)
    print(f"{target.id}: {'OK' if ok else 'MISSING'} {target.local_dir}")
PY
```

所有目标都应显示 `OK`。

### 4. 跑测试

```bash
python3 -m unittest discover -s tests
```

期望结果：

```text
OK
```

### 5. 执行同步

如果当前文件已经手动同步到飞书，并且不希望首次运行重复上传，可以先建立基线：

```bash
python3 main.py --mark-current-synced
```

如果希望首次运行就上传所有新增文件，直接执行：

```bash
python3 main.py
```

多目标同步时，输出应按 target 分段：

```text
开始从本地Markdown文件同步到飞书，共2个同步目标
开始同步目标: research
...
开始同步目标: work
...
同步完成：上传X个，跳过Y个，失败目标0个
```

### 6. 再跑一次确认增量跳过

```bash
python3 main.py
```

如果没有文件变化，第二次运行应看到：

```text
新增或变更0个，跳过未变化N个
```

## 自动同步

项目提供了 macOS `launchd` 配置，当前计划每天 05:00 执行。

### Terminal 执行脚本

自动任务会打开 Terminal 执行：

```text
/Users/yourname/projects/markdown2feishuDoc/scripts/run_sync.command
```

这样 iCloud Drive 的读取权限由 Terminal 承担，比让 `launchd` 后台直接运行 Python 更稳定。

如果项目路径或 Python 路径发生变化，需要同步修改：

- `scripts/run_sync.command`
- `scripts/com.yourname.markdown2feishu.sync.plist`

### 安装或重载 LaunchAgent

```bash
cp scripts/com.yourname.markdown2feishu.sync.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.yourname.markdown2feishu.sync.plist 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourname.markdown2feishu.sync.plist
launchctl enable gui/$(id -u)/com.yourname.markdown2feishu.sync
```

立即触发一次：

```bash
launchctl kickstart -k gui/$(id -u)/com.yourname.markdown2feishu.sync
```

查看任务状态：

```bash
launchctl print gui/$(id -u)/com.yourname.markdown2feishu.sync
```

## 日志

正常输出：

```bash
tail -80 logs/feishu_sync.out.log
```

错误输出：

```bash
tail -80 logs/feishu_sync.err.log
```

日志中常见的成功输出：

```text
找到4个Markdown文件
新增或变更0个，跳过未变化4个
Terminal sync exit: 0
```

## 同步状态

同步状态保存在项目根目录的 `.sync_state.json`，该文件已被 `.gitignore` 忽略。

状态内容包括：

- 同步目标 `id`。
- 每个目标下的 Markdown 相对路径。
- 文件 SHA-256。
- 文件大小。
- 已上传飞书文档的 `doc_token`。
- 已创建或复用的飞书文件夹 token。

这些信息用于判断文件是否变化，并在后续同步时复用已有飞书资源。

## 工作流程

1. 读取飞书应用凭证和同步目标配置。
2. 如果存在 `sync_targets.json`，读取多组同步目标；否则回退到旧版 `.env` 单目标配置。
3. 逐个同步目标规范化本地路径。
4. 扫描该目标下所有 Markdown 文件。
5. 检查 iCloud `.icloud` 占位文件。
6. 读取 `.sync_state.json` 中该目标的同步状态。
7. 筛选新增或内容变化的 Markdown。
8. 创建或复用飞书文件夹。
9. 上传 Markdown 并导入为飞书新版文档。
10. 上传并替换文档中的本地图片。
11. 如果存在旧文档，上传成功后删除旧文档。
12. 更新 `.sync_state.json`。
13. 清理临时文件。

## 文件命名规则

上传到飞书时，文档标题来自 Markdown 文件名。当前逻辑会从右向左按空格拆分一次，取前半部分作为标题。

例如：

```text
PyTorch 107d0087cdc38084920cd4b24c79eccb.md -> PyTorch
```

这个规则适合处理带 UUID 或时间戳后缀的导出文件。如果你的文件名本身包含空格，需要确认该规则是否符合预期。

## 图片处理

- 支持 Markdown 中的本地相对路径图片。
- 跳过网络 URL 图片。
- 图片会上传到飞书文档对应图片块。
- 上传时会读取图片尺寸，尽量保留原始显示比例。

## 常见问题

### 为什么定时任务要打开 Terminal？

`launchd` 后台进程直接读取 iCloud Drive 时，可能被 macOS 隐私权限拦截，表现为目录存在但无法列出文件。改为打开 Terminal 后，读取权限由 Terminal 承担，当前验证更稳定。

### 发现 `.icloud` 占位文件怎么办？

说明文件还没有真正下载到本机。先在 Finder 中打开对应目录，把文件下载完成后再运行同步。

### 修改 Markdown 后飞书出现重复文档怎么办？

当前版本会优先使用 `.sync_state.json` 中记录的旧 `doc_token`。如果状态里没有 token，会按父目录和文档名查找同名 `docx` 作为旧文档，并在新文档上传成功后删除旧文档。

### 为什么本地 target 有文件，但飞书上看不到？

先检查该 target 是否已经被标记为已同步：

```bash
python3 - <<'PY'
from src.sync_targets import load_sync_targets
from src.markdown_parser import MarkdownParser
from src.sync_state import SyncState

state = SyncState()
for target in load_sync_targets():
    files = MarkdownParser(target.local_dir).get_markdown_files()
    changed = [f for f in files if state.has_changed(f, target_id=target.id)]
    print(f"{target.id}: md={len(files)} changed={len(changed)}")
    for item in files:
        token = state.get_doc_token(item, target_id=target.id)
        print(f"  {item['relative_path']} changed={state.has_changed(item, target_id=target.id)} doc_token={'YES' if token else 'NO'}")
PY
```

如果某个 target 显示 `changed=0`，但对应文件的 `doc_token=NO`，通常说明之前执行过 `python3 main.py --mark-current-synced`。这个命令只记录当前文件状态，不会上传文件。

如果只想让某个 target 重新上传，可以先备份状态文件，再删除该 target 的状态。下面以 `work` 为例；实际使用时把 `target_id` 改成自己的同步目标 `id`。

```bash
cp .sync_state.json .sync_state.backup.json

python3 - <<'PY'
import json

target_id = "work"
path = ".sync_state.json"

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data.get("targets", {}).pop(target_id, None)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    f.write("\n")

print(f"removed {target_id} sync state")
PY
```

然后重新执行：

```bash
python3 main.py
```

### 是否支持飞书与本地双向同步？

不支持。当前功能只负责把本地 Markdown 的新增和变化同步到飞书。

## 项目结构

```text
markdown2feishuDoc/
├── main.py
├── requirements.txt
├── README.md
├── sync_targets.example.json
├── docs/
│   └── SYNC_AUTOMATION.md
├── scripts/
│   ├── com.yourname.markdown2feishu.sync.plist
│   └── run_sync.command
├── config/
│   ├── __init__.py
│   └── config.py
├── src/
│   ├── __init__.py
│   ├── feishu_client.py
│   ├── markdown_parser.py
│   ├── path_utils.py
│   ├── sync_targets.py
│   └── sync_state.py
└── tests/
    ├── test_feishu_client.py
    ├── test_markdown_parser.py
    ├── test_path_utils.py
    ├── test_sync_targets.py
    └── test_sync_state.py
```

## 核心依赖

| 包名 | 用途 |
| --- | --- |
| `lark-oapi` | 飞书开放平台 Python SDK |
| `Pillow` | 读取图片尺寸 |
| `python-dotenv` | 读取 `.env` 配置 |
| `requests` | HTTP 请求库 |

## 相关链接

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [飞书 Python SDK](https://github.com/larksuite/oapi-sdk-python)
- [Markdown 语法指南](https://www.markdownguide.org/)

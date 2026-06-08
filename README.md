# Markdown 到飞书自动同步工具

把本地 Markdown 目录单向同步到飞书云文档。工具会递归扫描 `.md` 文件，保留本地目录结构，只上传新增或内容变化的文件，并支持通过 macOS `launchd` 每天定时执行。

> 当前同步方向是 **本地 Markdown -> 飞书云文档**。不支持把飞书文档修改自动回写到本地。

## 功能特性

- 递归扫描本地 Markdown 目录，支持 iCloud Drive 路径。
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

在项目根目录创建 `.env`：

```bash
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
LOCAL_MARKDOWN_DIR=/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace
DEFAULT_PARENT_FOLDER_TOKEN=your_folder_token
```

如果从终端复制 iCloud 路径，可能会带反斜杠：

```text
/Users/molly/Library/Mobile\ Documents/com\~apple\~CloudDocs/researchspace
```

程序会自动规范化为 Python 可读取的路径：

```text
/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace
```

### 5. 手动同步

```bash
python3 main.py
```

首次启用定时同步前，如果当前飞书里已经有对应文档，可以先只记录当前文件状态，不上传：

```bash
python3 main.py --mark-current-synced
```

之后再次运行 `python3 main.py` 时，只会上传新增或内容变化的 Markdown。

## 自动同步

项目提供了 macOS `launchd` 配置，当前计划每天 05:00 执行。

### Terminal 执行脚本

自动任务会打开 Terminal 执行：

```text
/Users/molly/projects/markdown2feishuDoc/scripts/run_sync.command
```

这样 iCloud Drive 的读取权限由 Terminal 承担，比让 `launchd` 后台直接运行 Python 更稳定。

如果项目路径或 Python 路径发生变化，需要同步修改：

- `scripts/run_sync.command`
- `scripts/com.molly.markdown2feishu.sync.plist`

### 安装或重载 LaunchAgent

```bash
cp scripts/com.molly.markdown2feishu.sync.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.molly.markdown2feishu.sync.plist 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.molly.markdown2feishu.sync.plist
launchctl enable gui/$(id -u)/com.molly.markdown2feishu.sync
```

立即触发一次：

```bash
launchctl kickstart -k gui/$(id -u)/com.molly.markdown2feishu.sync
```

查看任务状态：

```bash
launchctl print gui/$(id -u)/com.molly.markdown2feishu.sync
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

- Markdown 相对路径。
- 文件 SHA-256。
- 文件大小。
- 已上传飞书文档的 `doc_token`。
- 已创建或复用的飞书文件夹 token。

这些信息用于判断文件是否变化，并在后续同步时复用已有飞书资源。

## 工作流程

1. 读取 `.env` 中的 `LOCAL_MARKDOWN_DIR`。
2. 规范化本地路径。
3. 扫描所有 Markdown 文件。
4. 检查 iCloud `.icloud` 占位文件。
5. 读取 `.sync_state.json`。
6. 筛选新增或内容变化的 Markdown。
7. 创建或复用飞书文件夹。
8. 上传 Markdown 并导入为飞书新版文档。
9. 上传并替换文档中的本地图片。
10. 如果存在旧文档，上传成功后删除旧文档。
11. 更新 `.sync_state.json`。
12. 清理临时文件。

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

### 是否支持飞书与本地双向同步？

不支持。当前功能只负责把本地 Markdown 的新增和变化同步到飞书。

## 项目结构

```text
markdown2feishuDoc/
├── main.py
├── requirements.txt
├── README.md
├── docs/
│   └── SYNC_AUTOMATION.md
├── scripts/
│   ├── com.molly.markdown2feishu.sync.plist
│   └── run_sync.command
├── config/
│   ├── __init__.py
│   └── config.py
├── src/
│   ├── __init__.py
│   ├── feishu_client.py
│   ├── markdown_parser.py
│   ├── path_utils.py
│   └── sync_state.py
└── tests/
    ├── test_feishu_client.py
    ├── test_markdown_parser.py
    ├── test_path_utils.py
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

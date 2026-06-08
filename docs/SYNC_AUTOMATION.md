# Markdown 到飞书自动同步说明

更新时间：2026-06-08

本文档记录本项目这次新增和修改的功能：iCloud Drive Markdown 读取、多目标配置、增量同步、飞书文档去重/更新、每天凌晨 5 点自动执行，以及最终采用的 Terminal 定时执行方案。

## 当前目标

把本机一个或多个 Markdown 文件夹自动同步到对应的飞书云文档文件夹，避免每天手动执行：

```bash
python3 main.py
```

示例 Markdown 来源目录：

```text
/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace
```

当前项目目录：

```text
/Users/molly/projects/markdown2feishuDoc
```

## 新增功能概览

1. 支持 `.env` 中配置 iCloud Drive 路径。
2. 支持从终端复制出来的带反斜杠路径自动规范化。
3. 支持通过 `sync_targets.json` 配置多组“本地目录 -> 飞书文件夹”映射。
4. 支持增量同步，只上传新增或内容变化的 Markdown。
5. 支持记录已上传文件状态，避免每天重复上传同一批文档。
6. 支持记录飞书文件夹 token，避免重复创建同名文件夹。
7. 支持记录飞书文档 token，后续同名文档变更时可删除旧文档并上传新文档。
8. 支持检测 iCloud `.icloud` 占位文件，并提示先下载到本机。
9. 支持每天凌晨 5 点通过 macOS `launchd` 自动触发同步。
10. 定时任务最终改为打开 Terminal 执行脚本，以绕过后台 Python 读取 iCloud Drive 被 macOS 隐私权限拦截的问题。

## 主要文件变更

### `main.py`

新增命令行参数：

```bash
python3 main.py --mark-current-synced
```

作用：只记录当前 Markdown 文件状态，不上传。适合首次启用定时同步前建立基线，避免已经上传过的文件在定时任务第一次运行时重复上传。

同步流程现在变为：

1. 读取 `sync_targets.json` 中的多组同步目标；如果该文件不存在，则回退到旧版 `.env` 单目标配置。
2. 使用 `normalize_config_path()` 规范化每个本地路径。
3. 逐个同步目标扫描 Markdown 文件。
4. 检查 iCloud `.icloud` 占位文件。
5. 读取 `.sync_state.json` 中该同步目标的状态。
6. 只筛选新增或内容变化的 Markdown。
7. 复用已记录或已存在的飞书文件夹。
8. 上传变化文件。
9. 上传成功后更新 `.sync_state.json`。

### `sync_targets.json`

新增多目标同步配置文件。示例：

```json
{
  "targets": [
    {
      "id": "research",
      "local_dir": "/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace",
      "feishu_folder_token": "your_research_folder_token"
    },
    {
      "id": "work",
      "local_dir": "/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/worknotes",
      "feishu_folder_token": "your_work_folder_token"
    }
  ]
}
```

`id` 用于隔离同步状态，避免不同本地目录下的同名 Markdown 在 `.sync_state.json` 中互相覆盖。真实的 `sync_targets.json` 已被 `.gitignore` 忽略，仓库只提交 `sync_targets.example.json`。

### 覆盖更新与去重修复（2026-06-08）

修复点：避免同一 `md` 多次修改后在飞书出现“新建一份旧版本 + 一份新版本”的重复文档。

1. 上传前先取 `doc_token`：优先使用 `.sync_state.json` 中记录的旧 token。
2. 当 state 中没有 token 时，按“父目录 + 文档名”查同名 `docx`，作为旧文档 fallback。
3. 上传成功后删除旧文档时做双保险：
   - 先按 `docx` 删除；
   - 失败后再按 `file` 删除；
   - 如果返回 `1061003 (not found)`，视为旧文档已不存在，视为幂等成功，不阻断本次同步。

修复范围文件：
- [/Users/molly/projects/markdown2feishuDoc/main.py](/Users/molly/projects/markdown2feishuDoc/main.py)
- [/Users/molly/projects/markdown2feishuDoc/src/feishu_client.py](/Users/molly/projects/markdown2feishuDoc/src/feishu_client.py)
- [/Users/molly/projects/markdown2feishuDoc/src/sync_state.py](/Users/molly/projects/markdown2feishuDoc/src/sync_state.py)

### `src/path_utils.py`

新增路径规范化函数：

```python
normalize_config_path(path)
```

它解决的问题是：Finder 或终端复制出来的 iCloud 路径可能长这样：

```text
/Users/molly/Library/Mobile\ Documents/com\~apple\~CloudDocs/researchspace
```

但 `.env` 和 Python 实际需要的是：

```text
/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace
```

该函数会自动去掉多余引号、首尾空格，并处理反斜杠转义。

### `src/sync_state.py`

新增同步状态管理。

默认状态文件：

```text
.sync_state.json
```

记录内容包括：

1. 每个同步目标的 `id`。
2. 目标内每个 Markdown 的相对路径。
3. 文件内容 SHA-256。
4. 文件大小。
5. 已上传飞书文档的 `doc_token`。
6. 已创建或复用的飞书文件夹 token。

这个文件用于判断文件是否变化，也是增量同步和避免重复创建文件夹的基础。

### `src/markdown_parser.py`

新增：

1. `relative_path` 字段，用作稳定的同步状态 key。
2. `get_icloud_placeholder_files()`，用于发现尚未下载到本机的 iCloud 占位文件。

如果存在 `.icloud` 文件，脚本会提示先在 Finder 中下载对应文件。

### `src/feishu_client.py`

新增和改进：

1. `format_response_error()`：飞书 API 失败时输出 `code/msg/raw`，避免只看到 Python 对象地址。
2. `get_child_folder_token()`：在父目录下查找同名文件夹，避免重复创建。
3. `get_child_doc_token()`：在父目录下查找同名文档。
4. `import_md_to_docx(..., existing_doc_token=...)`：上传新文档后，如果发现已有旧文档 token，会尝试删除旧文档。
5. `_delete_document()`：支持 `docx` + `file` 两种类型删除旧文档，`1061003` 作为旧文档不存在处理为幂等成功。
6. 所有主要飞书 API 失败路径都改为输出更具体的错误信息。

### `scripts/run_sync.command`

新增 Terminal 执行入口：

```text
/Users/molly/projects/markdown2feishuDoc/scripts/run_sync.command
```

它会：

1. 进入项目目录。
2. 使用真实 Python 可执行文件运行 `main.py`。
3. 把标准输出写入：

```text
/Users/molly/projects/markdown2feishuDoc/logs/feishu_sync.out.log
```

4. 把错误输出写入：

```text
/Users/molly/projects/markdown2feishuDoc/logs/feishu_sync.err.log
```

### `scripts/com.molly.markdown2feishu.sync.plist`

新增/更新 macOS LaunchAgent 配置。

当前定时任务每天凌晨 5 点执行：

```text
/usr/bin/open -a Terminal /Users/molly/projects/markdown2feishuDoc/scripts/run_sync.command
```

这样任务由 Terminal 执行，读取 iCloud Drive 的权限由 Terminal 承担，比后台 Python 直接访问 iCloud Drive 更稳定。

已安装的 LaunchAgent 位于：

```text
/Users/molly/Library/LaunchAgents/com.molly.markdown2feishu.sync.plist
```

## 为什么改为 Terminal 方案

最初尝试过让 `launchd` 直接执行 Python：

```text
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9
```

该方案可以启动脚本，但后台进程读取 iCloud Drive 目录时被 macOS 隐私权限拦截。诊断结果显示：

```text
exists: true
isdir: true
listdir_error: PermissionError(1, 'Operation not permitted')
md_count: 0
```

也就是说，后台进程知道目录存在，但不能列出目录内容，所以脚本显示：

```text
找到0个Markdown文件
```

改用 Terminal 后，实际验证已经可以看到：

```text
找到4个Markdown文件
新增或变更0个，跳过未变化4个
Terminal sync exit: 0
```

## 当前定时任务

任务名称：

```text
com.molly.markdown2feishu.sync
```

执行时间：

```text
每天 05:00
```

查看任务状态：

```bash
launchctl print gui/$(id -u)/com.molly.markdown2feishu.sync
```

立即触发一次：

```bash
launchctl kickstart -k gui/$(id -u)/com.molly.markdown2feishu.sync
```

重新加载任务：

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.molly.markdown2feishu.sync.plist 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.molly.markdown2feishu.sync.plist
launchctl enable gui/$(id -u)/com.molly.markdown2feishu.sync
```

## 日志查看

查看正常输出：

```bash
tail -80 /Users/molly/projects/markdown2feishuDoc/logs/feishu_sync.out.log
```

查看错误输出：

```bash
tail -80 /Users/molly/projects/markdown2feishuDoc/logs/feishu_sync.err.log
```

旧日志中可能存在以下历史错误，可以忽略：

```text
can't open file '/Users/molly/Downloads/markdown2feishuDoc/main.py'
read-only variable: status
找到0个Markdown文件
```

这些都是切换到新项目目录和 Terminal 方案之前留下的记录。

## 常用操作

### 手动运行同步

```bash
cd /Users/molly/projects/markdown2feishuDoc
python3 main.py
```

### 建立当前文件同步基线

如果你已经手动上传过当前文件，不希望下一次定时任务重复上传，可以执行：

```bash
cd /Users/molly/projects/markdown2feishuDoc
python3 main.py --mark-current-synced
```

### 通过 Terminal 入口手动运行

```bash
/Users/molly/projects/markdown2feishuDoc/scripts/run_sync.command
```

### 修改同步目标

优先编辑 `sync_targets.json`：

```json
{
  "targets": [
    {
      "id": "research",
      "local_dir": "/Users/molly/Library/Mobile Documents/com~apple~CloudDocs/researchspace",
      "feishu_folder_token": "your_research_folder_token"
    }
  ]
}
```

不要在配置中写终端转义格式：

```text
/Users/molly/Library/Mobile\ Documents/com\~apple\~CloudDocs/researchspace
```

## 权限要求

### 飞书权限

飞书开放平台应用需要有云文档、文件上传、导入任务、文档块读取/更新等权限，并且目标飞书文件夹需要把应用加入成员管理并给予编辑权限。

### macOS 权限

因为最终方案通过 Terminal 执行，建议在：

```text
系统设置 → 隐私与安全性 → 完全磁盘访问权限
```

给 Terminal 开启完全磁盘访问权限。

Terminal 路径通常是：

```text
/System/Applications/Utilities/Terminal.app
```

## 验证记录

已验证：

```text
找到4个Markdown文件
新增或变更0个，跳过未变化4个
Terminal sync exit: 0
```

单元测试已覆盖：

1. 飞书错误响应格式化。
2. iCloud 路径规范化。
3. Markdown 相对路径生成。
4. 增量同步状态判断。
5. 文档 token 和文件夹 token 的状态保存/读取。

运行测试：

```bash
cd /Users/molly/projects/markdown2feishuDoc
python3 -m unittest discover -s tests
```

## 当前行为边界

1. 当前同步是“文件新增/变化后上传到飞书”，不是飞书与本地的双向同步。
2. 本地删除 Markdown 后，脚本不会自动删除飞书上的文档。
3. Markdown 修改后会在有旧 `doc_token` 或同目录同名旧文档时做覆盖更新。
4. 旧文档删除如果返回 `1061003`，会按幂等语义跳过，不影响本次导入成功。
5. 如果 iCloud 文件尚未下载到本机，脚本不会上传 `.icloud` 占位文件，会提示先下载。
6. 定时任务每天 5 点会打开 Terminal 窗口执行同步。

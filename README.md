# Markdown 文档导入飞书在线文档工具

一个自动化工具,用于将本地 Markdown 文档批量导入到飞书云文档,支持文档内容转换和图片上传。

## 功能特性

- ✅ **批量导入**: 支持递归扫描目录下所有 Markdown 文件
- ✅ **自动转换**: 将 Markdown 格式自动转换为飞书云文档格式
- ✅ **图片上传**: 自动识别并上传 Markdown 中的本地图片
- ✅ **目录结构保留**: 自动创建对应的飞书文件夹层级结构
- ✅ **临时文件清理**: 导入完成后自动清理临时文件

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 创建飞书自建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app) 创建企业自建应用
2. 在「权限管理」中添加以下权限:
   - **云文档相关权限**(所有权限):
     - `drive:drive:readonly` - 查看云空间文件
     - `drive:drive:write` - 创建、编辑、上传云空间文件
     - `docx:document` - 查看、创建云文档
     - `docx:document:readonly` - 查看云文档
     - `drive:file` - 上传、下载文件到云空间
     - `drive:file:upload` - 上传文件
     - `drive:drive` - 查看、评论、编辑和管理云空间中所有文件
3. 获取应用的 **App ID** 和 **App Secret**

### 3. 配置文件夹权限

按照 [飞书官方教程](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-add-permissions-to-app) 给自建应用添加目标文件夹的权限:

1. 打开飞书云文档,选择目标文件夹
2. 点击「...」→「设置」→「成员管理」
3. 添加你的应用

### 4. 配置环境变量

在项目根目录创建 `.env` 文件,配置以下参数:

```bash
# 飞书应用凭证
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret

# 本地 Markdown 文档目录(绝对路径)
LOCAL_MARKDOWN_DIR=/path/to/your/markdown/files

# 飞书目标文件夹 Token
DEFAULT_PARENT_FOLDER_TOKEN=your_folder_token
```

**获取文件夹 Token 的方法**:

在浏览器中打开飞书云文档目标文件夹,URL 最后一段即为 folder token:

```
https://xxx.feishu.cn/drive/folder/xxxxxxxxxxxxx
                                    ↑
                               folder_token
```

![示例图片](img/image.png)

### 5. 运行程序

```bash
python3 main.py
```

## 项目结构

```
markdown2feishuDoc/
├── main.py                     # 主入口程序
├── requirements.txt            # Python 依赖
├── .env                        # 环境配置(需手动创建)
├── README.md                   # 本文档
├── config/
│   ├── __init__.py
│   └── config.py              # 配置管理模块
└── src/
    ├── __init__.py
    ├── feishu_client.py       # 飞书 API 客户端
    └── markdown_parser.py     # Markdown 解析器
```

## 核心依赖

| 包名 | 用途 |
|------|------|
| `lark-oapi` | 飞书开放平台官方 SDK |
| `Pillow` | 图片处理(获取尺寸信息) |
| `python-dotenv` | 环境变量管理 |
| `requests` | HTTP 请求库 |

## 使用说明

### 文件命名处理

本工具会自动处理文件名格式。如果你的 Markdown 文件名包含时间戳或 UUID 后缀(如从其他平台导出的文件):

```
示例: "PyTorch 107d0087cdc38084920cd4b24c79eccb.md"
处理后: "PyTorch"(在飞书中显示)
```

程序会**从右向左按空格拆分一次**,取第一个元素作为文档标题。

> 💡 **自定义需求**: 如果这个行为与你的需求冲突,可以修改 `main.py` 第 43 行和 `feishu_client.py` 第 52 行的文件名处理逻辑。

### 性能说明

由于飞书 API 的并发限制,本工具采用同步方式逐个上传文档,导入速度会相对较慢。

**优化建议**:
- 对于大批量导入场景,可以考虑:
  - 分批次导入
  - 在允许的情况下使用异步或多线程(需注意 API 限流)

### 图片处理

- ✅ 支持相对路径的本地图片
- ❌ 跳过网络 URL 图片
- ✅ 自动上传并关联到文档块
- ✅ 保留原始图片尺寸

## 常见问题

### Q: 为什么导入速度慢?

A: 飞书 API 有严格的并发限制,当前版本使用同步串行方式导入以确保稳定性。

### Q: 支持哪些 Markdown 语法?

A: 支持标准 Markdown 语法,具体转换效果取决于飞书云文档的支持范围。

### Q: 图片上传失败怎么办?

A: 检查以下几点:
1. 图片路径是否正确(相对于 Markdown 文件)
2. 图片格式是否支持(JPG、PNG 等)
3. 应用是否有足够的权限

### Q: 如何获取飞书应用凭证?

A: 在 [飞书开放平台控制台](https://open.feishu.cn/app) 的应用详情页可以查看 App ID,App Secret 需要在「凭证与基础信息」中查看。

## 技术细节

### 工作流程

1. **扫描阶段**: 递归扫描本地目录,收集所有 `.md` 文件
2. **文件夹创建**: 根据本地目录结构在飞书创建对应的文件夹层级
3. **文档上传**:
   - 上传 Markdown 文件到飞书云空间
   - 创建导入任务(Markdown → 飞书云文档)
   - 轮询任务状态直到转换完成
4. **图片处理**:
   - 解析 Markdown 中的图片引用
   - 上传图片到飞书
   - 更新文档图片块的引用
5. **清理阶段**: 删除临时上传的 Markdown 文件

### API 调用

主要使用以下飞书 API:

- `drive.v1.file.create_folder` - 创建文件夹
- `drive.v1.file.upload_all` - 上传文件
- `drive.v1.import_task.create` - 创建导入任务
- `drive.v1.import_task.get` - 查询任务状态
- `docx.v1.document_block.list` - 获取文档块
- `drive.v1.media.upload_all` - 上传图片
- `docx.v1.document_block.patch` - 更新文档块

## 贡献指南

欢迎提交 Issue 和 Pull Request!

## 许可证

MIT License


## 相关链接

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [飞书 Python SDK](https://github.com/larksuite/oapi-sdk-python)
- [Markdown 语法指南](https://www.markdownguide.org/)

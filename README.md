# markdown文档导入为飞书在线文档
本工具用于将markdown文档导入为飞书在线文档，暂时只支持导入markdown文档及其中图片。

## 使用方法
1. 安装依赖
```bash
pip3 install -r requirements.txt
```
2. 创建飞书自建应用，赋予应用云文档中的所有权限
请访问[飞书开发者平台](https://open.feishu.cn/app)进行配置，获取应用的app Id 和 app secret。保存到.env文件中。

3. 赋予应用特定文件夹的权限
[官方教程](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-add-permissions-to-app)

4. 配置
在.env中配置 LOCAL_MARKDOWN_DIR 为本地markdown文档的路径，配置 DEFAULT_PARENT_FOLDER_TOKEN 为飞书文件夹的token，其中token可以通过浏览器访问飞书文档获取， URL的最后一部分就是。
![示例图片](img/image.png)

5. 运行
```bash
python3 main.py
```

## 说明
* 因为飞书的api并发限制，目前并没有用异步或多线程，所以导入速度较慢。如果导入量较大，可以考虑使用异步或多线程。

* 因为作者在其他平台导出的markdown在原有文件名的基础上还会加空格拼接上时间戳或UUID（例如："PyTorch 107d0087cdc38084920cd4b24c79eccb"），所以在导入时会自动从右向左按空格截取一次取第一个元素凭借上.md后缀作为文件名。（当然导入为飞书云文档不会带上文件名）,如和你的需求有冲突，可以自行修改代码。


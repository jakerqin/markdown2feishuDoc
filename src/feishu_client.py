import json
import os
import time
from typing import List, Optional
import lark_oapi as lark
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.docx.v1 import *
from PIL import Image

from config.config import FEISHU_APP_ID, FEISHU_APP_SECRET, DEFAULT_PARENT_FOLDER_TOKEN
from src.markdown_parser import MarkdownParser


def format_response_error(action, resp):
    parts = [action]

    code = getattr(resp, "code", None)
    if code is not None:
        parts.append(f"code={code}")

    msg = getattr(resp, "msg", None)
    if msg:
        parts.append(f"msg={msg}")

    raw = getattr(resp, "raw", None)
    content = getattr(raw, "content", None)
    if content:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        parts.append(f"raw={content}")

    return ": ".join([parts[0], ", ".join(parts[1:])]) if len(parts) > 1 else action


class FeishuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.default_parent_folder_token = DEFAULT_PARENT_FOLDER_TOKEN
        
        # 初始化 SDK 客户端
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()

        # 获取访问令牌
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        """获取飞书访问令牌"""
        request: InternalTenantAccessTokenRequest = InternalTenantAccessTokenRequest.builder() \
            .request_body(InternalTenantAccessTokenRequestBody.builder()
                .app_id(self.app_id)
                .app_secret(self.app_secret)
            .build()) \
        .build()
        resp:InternalTenantAccessTokenResponse = self.client.auth.v3.tenant_access_token.internal(request)
        if resp.code != 0:
            raise Exception(format_response_error("获取访问令牌失败", resp))
        
        return json.loads(resp.raw.content).get('tenant_access_token')
        
    def create_folder(self, folder_name, parent_token=None):
        """创建飞书云文档文件夹
        Args:
            folder_name: 文件夹名称
            parent_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            str: 创建的文件夹 token
        """
        req = CreateFolderFileRequest.builder() \
            .request_body(CreateFolderFileRequestBody.builder()
                         .name(folder_name)
                         .folder_token(parent_token if parent_token else "")
                         .build()) \
            .build()
        
        resp:CreateFolderFileResponse = self.client.drive.v1.file.create_folder(req)
        if resp.code != 0:
            raise Exception(format_response_error("创建文件夹失败", resp))
            
        return resp.data.token

    def get_child_folder_token(self, parent_token, folder_name):
        """查找父目录下的同名文件夹 token"""
        candidate_names = {folder_name}
        fallback_name = folder_name.rsplit(" ", 1)[0]
        if fallback_name:
            candidate_names.add(fallback_name)

        request = ListFileRequest.builder() \
            .folder_token(parent_token) \
            .page_size(200) \
            .build()

        while True:
            response: ListFileResponse = self.client.drive.v1.file.list(request)
            if response.code != 0:
                raise Exception(format_response_error("查询文件夹失败", response))

            files = response.data.files or []
            for file_info in files:
                if file_info.type == "folder" and file_info.name in candidate_names:
                    return file_info.token

            if not response.data.has_more:
                break

            request.page_token = response.data.next_page_token

        return None

    def get_child_doc_token(self, parent_token, doc_name):
        """查找父目录下同名文档 token"""
        request = ListFileRequest.builder() \
            .folder_token(parent_token) \
            .page_size(200) \
            .build()

        while True:
            response: ListFileResponse = self.client.drive.v1.file.list(request)
            if response.code != 0:
                raise Exception(format_response_error("查询文档失败", response))

            files = response.data.files or []
            for file_info in files:
                if file_info.type == "docx" and file_info.name == doc_name:
                    return file_info.token

            if not response.data.has_more:
                break

            request.page_token = response.data.next_page_token

        return None

    def _upload_md_to_cloud(self, title, file_size, folder_token, md_content) -> str:
        """md文件导入飞书文档
        """
        print(f"[DEBUG] 开始上传MD文件")
        print(f"[DEBUG] 文件名: {title}.md")
        print(f"[DEBUG] 文件大小: {file_size} bytes")
        print(f"[DEBUG] 目标文件夹token: {folder_token}")
        
        file_req: UploadAllFileRequest = UploadAllFileRequest.builder() \
            .request_body(UploadAllFileRequestBody.builder()
                .file_name(title + ".md")
                .parent_type("explorer")
                .parent_node(folder_token)
                .size(file_size)
                .file(md_content)
                .build()) \
        .build()

        
        file_resp: UploadAllFileResponse = self.client.drive.v1.file.upload_all(file_req)
        
        # 打印详细响应信息
        print(f"[DEBUG] 响应code: {file_resp.code}")
        print(f"[DEBUG] 响应msg: {file_resp.msg}")
        if hasattr(file_resp, 'raw') and file_resp.raw:
            print(f"[DEBUG] 原始响应: {file_resp.raw.content}")
        if file_resp.data:
            print(f"[DEBUG] 响应data: {file_resp.data}")
        
        if file_resp.code != 0:
            raise Exception(format_response_error("上传md文件失败", file_resp))
        # 获取上传任务ID
        return file_resp.data.file_token

    def _create_import_task(self, file_token, title, folder_token) -> str:
        """创建md文件导入为云文档任务
        args:
            file_token: md文件的token
            title: 文档标题
            folder_token: 文档所在文件夹的token
        returns:
            ticket: 导入任务的ticket
        """
        # 创建md文件导入为云文档
        import_req: CreateImportTaskRequest = CreateImportTaskRequest.builder() \
            .request_body(ImportTask.builder()
                .file_extension("md")
                .file_token(file_token)
                .type("docx")
                .file_name(title)
                .point(ImportTaskMountPoint.builder()
                    .mount_type(1)
                    .mount_key(folder_token)
                    .build())
                .build()) \
        .build()

        import_resp: CreateImportTaskResponse = self.client.drive.v1.import_task.create(import_req)
        if import_resp.code != 0:
            raise Exception(format_response_error("创建导入任务失败", import_resp))
        return import_resp.data.ticket 

    def _get_import_docx_token(self, ticket) -> str:
        """轮询导入任务状态，获取导入文档的token
        args:
            ticket: 导入任务的ticket
        returns:
            docx_token: 导入文档的token
        """
        request: GetImportTaskRequest = GetImportTaskRequest.builder() \
            .ticket(ticket) \
        .build()

        while True:
            response: GetImportTaskResponse = self.client.drive.v1.import_task.get(request)
            if response.code != 0:
                raise Exception(format_response_error("获取导入任务状态失败", response))

            job_status = response.data.result.job_status
            if job_status == 0:  # 处理成功
                print(f"[DEBUG] 导入文档成功")
                return response.data.result.token
            elif job_status == 1 or job_status == 2:  # 初始化或处理中
                print("任务处理中...")
            else:  # job_status == 3，处理失败
                raise Exception(f"任务处理失败：{response.data.result.job_error_msg}")
                
            # 等待一段时间后再次查询状态
            time.sleep(2)
        

    def import_md_to_docx(self, file_path, title, folder_token, existing_doc_token: Optional[str] = None):
        """md文件导入飞书文档
        """
        # 读取并解析Markdown文件
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        file_size = os.path.getsize(file_path)

        # 提取出markdown的所有图片路径
        img_path_list: List = MarkdownParser.extract_images_from_markdown(file_path, md_content)


        # 上传md文件, 获取file_token
        file_token = self._upload_md_to_cloud(title, file_size, folder_token, md_content)

        # 创建md文件导入为云文档, 获取ticket
        ticket = self._create_import_task(file_token, title, folder_token)

        # 轮询导入任务状态，获取导入文档的token
        doc_token = self._get_import_docx_token(ticket)

        # 把markdown中记录的图片路径，上传图片到飞书文档，更新image block的image_key
        if img_path_list:
            self._update_document_images(doc_token, img_path_list)

        # 如果已有旧文档，更新策略是：先创建新文档，再删除旧文档，确保只保留一份目标文档
        if existing_doc_token and existing_doc_token != doc_token:
            self._delete_document(existing_doc_token)

        # 删除上传的md文件
        self._del_file(file_token)
        return doc_token

    def _update_document_images(self, doc_token, img_path_list: List):
        """更新文档中的图片
        Args:
            doc_token: 文档token
            ima_path_list: markdown中记录的图片地址列表
        """
        # 获取文档所有块
        request: ListDocumentBlockRequest = ListDocumentBlockRequest.builder() \
            .page_size(500) \
            .document_id(doc_token) \
            .document_revision_id(-1) \
        .build()
        # 访问img_path_list的索引位置
        img_path_index = 0

        while True:
            resp: ListDocumentBlockResponse = self.client.docx.v1.document_block.list(request)
            if resp.code != 0:
                raise Exception(f"获取文档块失败: {resp}")
                
            # 遍历所有块
            for block in resp.data.items:
                # 检查是否为图片块
                if block.block_type == 27 and img_path_index < len(img_path_list): # 图片块
                    # 上传图片到飞书文档指定的 block 中
                    img_path = img_path_list[img_path_index]
                    image_token = self._upload_image_to_doc(img_path, block.block_id, doc_token)
                    img_path_index += 1

                    # 更新图片块的image_key
                    self._update_doc_image_block(img_path, block.block_id, doc_token, image_token)
            
            # 检查是否还有更多块
            if not resp.data.has_more:
                break
                
            # 更新请求参数，获取下一页
            request.page_token = resp.data.page_token

    def _upload_image_to_doc(self, file_path, block_id, document_id):
        """上传图片到飞书文档, 这个图片跟文档绑定在一起，删除文档时图片也会被删除，方便管理
        Args:
            image_path: 图片路径
        Returns:
            str: 图片的 token
        """
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        image_content = open(file_path, "rb")

        extra: dict = { "drive_route_token": document_id }
        request: UploadAllMediaRequest = UploadAllMediaRequest.builder() \
            .request_body(UploadAllMediaRequestBody.builder()
                .file_name(file_name)
                .parent_node(block_id)
                .parent_type("docx_image")
                .size(file_size)
                .extra(json.dumps(extra, ensure_ascii=False, indent=2))  
                .file(image_content)
            .build()) \
        .build()
        
        resp: UploadAllMediaResponse = self.client.drive.v1.media.upload_all(request)
        if resp.code != 0:
            raise Exception(format_response_error("上传图片到云文档失败", resp))
        print(f"上传图片到云文档成功: {resp}")
        return resp.data.file_token

    def _update_doc_image_block(self, file_path, block_id, document_id, image_token):
        """更新文档中的图片块
        Args:
            block_id: 图片块的 id
            document_id: 文档的 id
            image_token: 图片的 token
        """
        # 获取图片尺寸
        with Image.open(file_path) as img:
            width, height = img.size
            print(f"图片尺寸: {width}x{height}")

        # 更新图片块的image_key
        request: PatchDocumentBlockRequest = PatchDocumentBlockRequest.builder() \
            .document_id(document_id) \
            .block_id(block_id) \
            .document_revision_id(-1) \
            .request_body(UpdateBlockRequest.builder()
                .replace_image(ReplaceImageRequest.builder()
                    .token(image_token)
                    .width(width)
                    .height(height)
                    .build())
                .build()) \
        .build()

        # 发起请求
        response: PatchDocumentBlockResponse = self.client.docx.v1.document_block.patch(request)
        if response.code != 0:
            raise Exception(format_response_error("更新图片块失败", response))
        print("更新图片块成功")

    def _del_file(self, file_token):
        """删除文件
        """
        request: DeleteFileRequest = DeleteFileRequest.builder() \
           .file_token(file_token) \
           .type("file")  \
        .build()
        resp: DeleteFileResponse = self.client.drive.v1.file.delete(request)
        if resp.code!= 0:
            raise Exception(format_response_error("删除文件失败", resp))
        print("删除文件成功")

    def _delete_document(self, doc_token):
        """删除文档文件"""
        last_not_found = False
        for file_type in ("docx", "file"):
            request: DeleteFileRequest = DeleteFileRequest.builder() \
                .file_token(doc_token) \
                .type(file_type) \
            .build()
            resp: DeleteFileResponse = self.client.drive.v1.file.delete(request)

            if resp.code == 0:
                print(f"删除旧文档成功 (type={file_type}): {doc_token}")
                return

            if self._is_old_doc_not_found(resp):
                last_not_found = True
                continue

            # 与临时md文件保持行为一致，其他错误直接抛错，避免静默导致重复文件
            raise Exception(format_response_error("删除旧文档失败", resp))

        if last_not_found:
            print(f"旧文档不存在或已被删除，跳过删除: {doc_token}")
            return

    @staticmethod
    def _is_old_doc_not_found(resp):
        return str(getattr(resp, "code", "")) == "1061003"

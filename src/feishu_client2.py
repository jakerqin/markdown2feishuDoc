import json
import time
from typing import Dict, Optional, Union
from lark_oapi import Config, Logger, LEVEL_DEBUG
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.authen.v1 import *
from lark_oapi.api.drive import upload_image
from lark_oapi.api.drive import download_media

class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        # SDK配置初始化
        self.config = Config(
            domain="open.feishu.cn",
            app_id=app_id,
            app_secret=app_secret,
            logger=Logger(LEVEL_DEBUG),  # 生产环境可关闭DEBUG日志
            disable_token_cache=False
        )
        self._tenant_access_token = None
        self._token_expire_time = 0

    def _ensure_token_valid(self):
        """确保tenant_access_token有效"""
        if time.time() < self._token_expire_time - 60:  # 提前60秒刷新
            return
        # 调用SDK获取token
        req = InternalAppAccessTokenRequest.builder().request_body(
            InternalAppAccessTokenRequestBody.builder()
                .app_id(self.config.app_id)
                .app_secret(self.config.app_secret)
                .build()
        ).build()
        resp = InternalAppAccessToken(self.config).request(req)
        if not resp.success():
            raise Exception(f"获取tenant_access_token失败: {resp.msg}")
        self._tenant_access_token = resp.data.app_access_token
        self._token_expire_time = time.time() + resp.data.expire  # 设置过期时间

    def get_tenant_access_token(self) -> str:
        """获取当前有效的tenant_access_token"""
        self._ensure_token_valid()
        return self._tenant_access_token

    def create_folder(self, folder_name: str, parent_node: str = "root") -> str:
        """在指定父节点下创建文件夹（默认在根目录）"""
        self._ensure_token_valid()
        req = CreateFolderFileRequest.builder().request_body(
            CreateFolderFileRequestBody.builder()
                .name(folder_name)
                .folder_token(parent_node)
                .build()
        ).build()
        resp = CreateFolderFile(self.config).request(req)
        if not resp.success():
            raise Exception(f"创建文件夹失败: {resp.msg}")
        return resp.data.token

    def create_document(self, title: str) -> str:
        """创建空白云文档"""
        self._ensure_token_valid()
        req = CreateDocumentRequest.builder().request_body(
            CreateDocumentRequestBody.builder()
                .title(title)
                .build()
        ).build()
        resp = CreateDocument(self.config).request(req)
        if not resp.success():
            raise Exception(f"创建文档失败: {resp.msg}")
        return resp.data.document.document_id

    def add_document_block(self, document_id: str, content: Dict) -> str:
        """向文档中添加内容块（需构造Block结构）"""
        self._ensure_token_valid()
        req = CreateDocumentBlockRequest.builder().document_id(document_id).request_body(
            Block.builder().children([content]).build()
        ).build()
        resp = CreateDocumentBlock(self.config).request(req)
        if not resp.success():
            raise Exception(f"添加文档块失败: {resp.msg}")
        return resp.data.block_id

    def upload_image(self, image_path: str) -> str:
        """上传图片并返回素材token"""
        self._ensure_token_valid()
        req = UploadImageRequest.builder().request(
            UploadImageRequestReq.builder()
                .image_type("message")
                .image(open(image_path, "rb"))
                .build()
        ).build()
        resp = upload_image(self.config).request(req)
        if not resp.success():
            raise Exception(f"上传图片失败: {resp.msg}")
        return resp.data.image_key

    def set_document_permission(
        self, document_token: str, user_id: str, perm: str = "edit"
    ) -> bool:
        """设置文档权限（perm可选：view/edit）"""
        self._ensure_token_valid()
        req = PatchPermissionRequest.builder().document_token(document_token).request_body(
            PatchPermissionRequestBody.builder()
                .members([{"member_type": "user", "member_id": user_id, "perm": perm}])
                .build()
        ).build()
        resp = PatchPermission(self.config).request(req)
        return resp.success()
    
    def get_first_user_info(self) -> Optional[Dict]:
        """获取通讯录中第一个用户的信息（需开通contact:user:read权限）"""
        self._ensure_token_valid()
        req = ListUserRequest.builder().page_size(1).build()
        resp = ListUser(self.config).request(req)
        
        if not resp.success() or not resp.data.items:
            return None
        
        user = resp.data.items[0]
        return {
            "user_id": user.user_id,
            "name": user.name,
            "mobile": user.mobile,
            "email": user.email,
            "department_ids": user.department_ids
        }

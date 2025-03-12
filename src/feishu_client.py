import json
import os
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.docx.v1 import *
from lark_oapi.core.const import *
from lark_oapi.core.utils import *
from lark_oapi.core import Config, Client, setup_logging
from config.config import FEISHU_APP_ID, FEISHU_APP_SECRET

class FeishuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        # 配置 SDK
        config = Config.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(logging.INFO) \
            .build()
        # 初始化 SDK 客户端
        self.client = Client(config)
        # 获取访问令牌
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        """获取飞书访问令牌"""
        req = CreateTenantAccessTokenReq.builder() \
            .body(CreateTenantAccessTokenReqBody.builder()
                  .app_id(self.app_id)
                  .app_secret(self.app_secret)
                  .build()) \
            .build()
        resp = self.client.auth.v3.tenant_access_token.create(req)
        if resp.code != 0:
            raise Exception(f"获取访问令牌失败: {resp}")
        return resp.tenant_access_token
        
    def create_folder(self, folder_name, parent_token=None):
        """创建飞书云文档文件夹
        Args:
            folder_name: 文件夹名称
            parent_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            str: 创建的文件夹 token
        """
        folder_name = folder_name.split(' ', 1)[0]  # 从右侧按空格拆分一次，取第一部分
        
        req = CreateFolderReq.builder() \
            .request_body(CreateFolderReqBody.builder()
                         .name(folder_name)
                         .folder_token(parent_token if parent_token else "")
                         .build()) \
            .build()
        
        resp = self.client.drive.v1.folder.create(req)
        if resp.code != 0:
            raise Exception(f"创建文件夹失败: {resp}")
            
        return resp.data.token

    def create_document(self, title, blocks, folder_token=None):
        """创建飞书文档
        Args:
            title: 文档标题
            blocks: 文档内容块
            folder_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            dict: 创建文档的响应结果
        """
        # 格式化内容块
        formatted_blocks = self._format_blocks_for_feishu(blocks)
        
        req = CreateDocumentReq.builder() \
            .request_body(CreateDocumentReqBody.builder()
                         .title(title)
                         .folder_token(folder_token if folder_token else "")
                         .content(formatted_blocks)
                         .build()) \
            .build()
        
        resp = self.client.docx.v1.document.create(req)
        if resp.code != 0:
            raise Exception(f"创建文档失败: {resp}")
            
        return resp.data

    def upload_image(self, image_path):
        """上传图片到飞书文档
        Args:
            image_path: 图片路径
        Returns:
            str: 图片的 token
        """
        with open(image_path, 'rb') as f:
            file_content = f.read()
        
        file_name = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        
        req = UploadAllMediaReq.builder() \
            .request_body(UploadAllMediaReqBody.builder()
                         .file_name(file_name)
                         .file_size(file_size)
                         .parent_type("docx_image")
                         .file(file_content)
                         .build()) \
            .build()
        
        resp = self.client.drive.v1.media.upload_all(req)
        if resp.code != 0:
            raise Exception(f"上传图片失败: {resp}")
                
        return resp.data.file_token

    def _format_blocks_for_feishu(self, blocks):
        """将块转换为飞书文档格式"""
        content = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "paragraph":
                content.append({
                    "paragraph": {
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type in ["heading1", "heading2", "heading3"]:
                level = int(block_type[-1])
                content.append({
                    "paragraph": {
                        "style": {"headingLevel": level},
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type == "image":
                content.append({
                    "image": {
                        "token": block.get("image_key", "")
                    }
                })
            elif block_type == "bullet":
                content.append({
                    "paragraph": {
                        "style": {"list": {"type": "bullet"}},
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type == "ordered":
                content.append({
                    "paragraph": {
                        "style": {"list": {"type": "number"}},
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type == "table":
                rows = block.get("rows", [])
                if rows:
                    table_data = {
                        "table": {
                            "columns": len(rows[0]) if rows else 0,
                            "rows": len(rows),
                            "cells": []
                        }
                    }
                    
                    for i, row in enumerate(rows):
                        for j, cell in enumerate(row):
                            table_data["table"]["cells"].append({
                                "row": i,
                                "col": j,
                                "elements": [{"text": cell}]
                            })
                    
                    content.append(table_data)
            elif block_type == "code":
                content.append({
                    "code": {
                        "language": block.get("language", "plain_text"),
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type == "quote":
                content.append({
                    "paragraph": {
                        "style": {"quote": {}},
                        "elements": [{"text": block.get("content", "")}]
                    }
                })
            elif block_type == "divider":
                content.append({
                    "divider": {}
                })
        
        return content
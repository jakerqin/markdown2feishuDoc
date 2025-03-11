import requests
import json
from config.config import FEISHU_APP_ID, FEISHU_APP_SECRET

class FeishuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        """获取飞书访问令牌"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()["tenant_access_token"]
        

    def create_folder(self, folder_name, parent_token=None):
        """创建飞书云文档文件夹
        Args:
            folder_name: 文件夹名称
            parent_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            str: 创建的文件夹 token
        """
        url = "https://open.feishu.cn/open-apis/drive/v1/files/create_folder"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "name": folder_name.split(' ', 1)[0],         # 从右侧按空格拆分一次，取第一部分
            "folder_token": parent_token if parent_token else ""
        }
            
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"创建文件夹失败: {result}")
            
        return result["data"]["token"]


    def create_document(self, title, blocks, folder_token=None):
        """创建飞书文档
        Args:
            title: 文档标题
            blocks: 文档内容块
            folder_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            dict: 创建文档的响应结果
        """
        url = "https://open.feishu.cn/open-apis/docx/v1/documents/create"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "title": title,
            "folder_token": folder_token if folder_token else "",
            "content": blocks
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"创建文档失败: {result}")
            
        return result["data"]

    def upload_image(self, image_path):
        """上传图片到飞书文档
        Args:
            image_path: 图片路径
        Returns:
            str: 图片的 token
        """
        url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        with open(image_path, 'rb') as f:
            files = {
                'file': f,
                'parent_type': (None, 'docx_image'),
            }
            response = requests.post(url, headers=headers, files=files)
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"上传图片失败: {result}")
                
            return result["data"]["file_token"]

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
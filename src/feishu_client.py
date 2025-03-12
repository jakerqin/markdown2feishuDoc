import json
import os
from typing import List
import lark_oapi as lark
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.docx.v1 import *

from config.config import FEISHU_APP_ID, FEISHU_APP_SECRET, DEFAULT_PARENT_FOLDER_TOKEN

class FeishuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.default_parent_folder_token = DEFAULT_PARENT_FOLDER_TOKEN
        
        # 初始化 SDK 客户端
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
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
            raise Exception(f"获取访问令牌失败: {resp}")
        
        return json.loads(resp.raw.content).get('tenant_access_token')
        
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
        
        resp = self.client.drive.v1.file.create_folder(req)
        if resp.code != 0:
            raise Exception(f"创建文件夹失败: {resp}")
            
        return resp.data.token

    def create_document(self, title, folder_token=None):
        """创建空的飞书文档
        Args:
            title: 文档标题
            folder_token: 父文件夹的 token，如果为 None 则创建在根目录
        Returns:
            dict: 创建文档的响应结果
        """
        # 格式化内容块
        # formatted_blocks = self._format_blocks_for_feishu(blocks)

        
        req: CreateDocumentRequest = CreateDocumentRequest.builder() \
            .request_body(CreateDocumentRequestBody.builder()
                .folder_token(folder_token if folder_token else "") 
                .title(title.split(' ', 1)[0])   # 从右侧按空格拆分一次，取第一部分
            .build()) \
        .build()

        resp = self.client.docx.v1.document.create(req)
        if resp.code != 0:
            raise Exception(f"创建文档失败: {resp}")
            
        return resp.data

    def update_document_block(self, document_id, markdown_content: List, block_id):
        """创建飞书文档的文档块
        Args:
            document_id: 文档Id
            block_id: 文档块Id，没有就是从文档根创建，document_id就是block_id
            document_revision_id: -1
            markdown_content: md内容 
        Returns:
            dict: 创建文档的响应结果
        """
        # 格式化内容块为飞书云文档的
        formatted_blocks = self._format_blocks_for_feishu(blocks)
        
        request: CreateDocumentBlockChildrenRequest = CreateDocumentBlockChildrenRequest.builder() \
            .document_revision_id(-1) \
            .document_id(document_id) \
            .request_body(CreateDocumentBlockChildrenRequestBody.builder() \
                .children(formatted_blocks)
            .index(0)
            .build()) \
        .build()

        # 发起请求
        response: CreateDocumentBlockChildrenResponse = self.client.docx.v1.document_block_children.create(request)
        
        # 调用飞书 API 更新文档
        resp = self.client.docx.v1.document_block.update(req)
        if resp.code != 0:
            raise Exception(f"更新文档块失败: {resp}")
            
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

    def _format_blocks_for_feishu(self, blocks) -> List[Block]:
        """将块转换为飞书文档格式的 Block 对象列表"""
        content = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "paragraph":
                text = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().text(text).build())
                
            elif block_type == "heading1":
                text = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().heading1(text).build())

            elif block_type == "heading2":
                text = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().heading2(text).build())

            elif block_type == "heading3":
                text = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().heading3(text).build())
                
            elif block_type == "image":
                # todo image_key 应该是飞书云文档的图片key
                image = Image.builder().token(block.get("image_key", "")).build()
                content.append(Block.builder().image(image).build())
                
            elif block_type == "bullet":
                bullet = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().bullet(bullet).build())
                
            elif block_type == "ordered":
                text = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().ordered(text).build())
                
            # elif block_type == "table":
            #     rows = block.get("rows", [])
            #     if rows:
            #         cells = []
            #         for i, row in enumerate(rows):
            #             for j, cell_text in enumerate(row):
            #                 cell = TableCell.builder().row(i).col(j).elements([
            #                     TextRun.builder().text(cell_text).build()
            #                 ]).build()
            #                 cells.append(cell)
                    
            #         table = Table.builder().cells(cells).build()
            #         content.append(Block.builder().table(table).build())
                
            elif block_type == "code":
                code = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().code(code).build())
                
            elif block_type == "quote":
                quote = Text.builder().style(TextStyle.builder().build()).elements([
                    TextElement.builder().text_run(TextRun.builder().content(block.get("content", ""))).build()
                ]).build()
                content.append(Block.builder().quote(quote).build())
                
            elif block_type == "divider":
                divider = Divider.builder().build()
                content.append(Block.builder().divider(divider).build())
        
        return content
import os
import re
import uuid
import markdown
from bs4 import BeautifulSoup
from urllib.parse import unquote
from dotenv import load_dotenv
from typing import List

load_dotenv()

class MarkdownParser:
    def __init__(self, markdown_dir):
        self.markdown_dir = markdown_dir
        
    def get_markdown_files(self):
        """获取所有Markdown文件"""
        markdown_files = []
        
        for root, dirs, files in os.walk(self.markdown_dir):
            for file in files:
                if file.endswith('.md'):
                    rel_dir = os.path.relpath(root, self.markdown_dir)
                    if rel_dir == '.':
                        rel_dir = ''
                    markdown_files.append({
                        'path': unquote(os.path.join(root, file)),
                        'name': os.path.splitext(file)[0],
                        'folder': rel_dir
                    })
        
        return markdown_files
    
    @staticmethod
    def extract_images_from_markdown(file_path, content):
        """从Markdown中提取图片路径"""
        
        # 查找Markdown中的图片链接
        image_paths = []
        pattern = r'!\[.*?\]\((.*?)\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # 处理相对路径
            if not match.startswith(('http://', 'https://')):
                img_path = os.path.join(os.path.dirname(file_path), match)
                # 处理有汉字的情况 被转换成url编码
                decoded_path = unquote(img_path)
                if os.path.exists(decoded_path):
                    image_paths.append(decoded_path)
        
        return image_paths
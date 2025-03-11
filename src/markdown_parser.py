import os
import re
import uuid
import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

class MarkdownParser:
    def __init__(self):
        self.markdown_dir = os.getenv('LOCAL_MARKDOWN_DIR')
        self.temp_dir = "./temp"
        os.makedirs(f"{self.temp_dir}/images", exist_ok=True)
        
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
                        'path': os.path.join(root, file),
                        'name': os.path.splitext(file)[0],
                        'folder': rel_dir
                    })
        
        return markdown_files
    
    def parse_markdown_file(self, file_path, feishu_client=None):
        """解析Markdown文件内容并上传图片到飞书
        Args:
            file_path: Markdown文件路径
            feishu_client: 飞书客户端实例，用于上传图片
        Returns:
            list: 解析后的内容块列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 解析Markdown为HTML
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析为块
        blocks = []
        
        # 处理标题
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                blocks.append({
                    'type': f'heading{min(i, 3)}',  # 飞书最多支持三级标题
                    'content': heading.get_text()
                })
                
        # 处理段落
        for p in soup.find_all('p'):
            # 检查是否包含图片
            img = p.find('img')
            if img and img.get('src'):
                img_src = img.get('src')
                # 处理相对路径
                if not img_src.startswith(('http://', 'https://')):
                    img_path = os.path.join(os.path.dirname(file_path), img_src)
                    if os.path.exists(img_path) and feishu_client:
                        try:
                            # 上传图片到飞书云空间
                            image_token = feishu_client.upload_image(img_path)
                            blocks.append({
                                'type': 'image',
                                'image_key': image_token  # 使用上传后的token
                            })
                        except Exception as e:
                            print(f"上传图片失败: {img_path}, 错误: {str(e)}")
                    continue
            
            # 普通段落
            if p.get_text().strip():
                blocks.append({
                    'type': 'paragraph',
                    'content': p.get_text()
                })
        
        # 处理列表
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li', recursive=False):
                blocks.append({
                    'type': 'bullet',
                    'content': li.get_text()
                })
                
        for ol in soup.find_all('ol'):
            for li in ol.find_all('li', recursive=False):
                blocks.append({
                    'type': 'ordered',
                    'content': li.get_text()
                })
        
        # 处理代码块
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                # 尝试获取语言类型
                language = 'plain_text'
                if 'class' in code.attrs:
                    classes = code.get('class')
                    for cls in classes:
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                            break
                
                blocks.append({
                    'type': 'code',
                    'content': code.get_text(),
                    'language': language
                })
        
        # 处理表格
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text() for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if rows:
                blocks.append({
                    'type': 'table',
                    'rows': rows
                })
        
        # 处理引用
        for blockquote in soup.find_all('blockquote'):
            blocks.append({
                'type': 'quote',
                'content': blockquote.get_text().strip()
            })
        
        # 处理分割线
        for hr in soup.find_all('hr'):
            blocks.append({
                'type': 'divider'
            })
            
        return blocks
    
    def extract_images_from_markdown(self, file_path):
        """从Markdown中提取图片路径"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找Markdown中的图片链接
        image_paths = []
        pattern = r'!\[.*?\]\((.*?)\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # 处理相对路径
            if not match.startswith(('http://', 'https://')):
                img_path = os.path.join(os.path.dirname(file_path), match)
                if os.path.exists(img_path):
                    image_paths.append(img_path)
        
        return image_paths
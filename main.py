import os
import shutil
import time
from dotenv import load_dotenv
from src.markdown_parser import MarkdownParser
from src.feishu_client import FeishuClient
from config.config import LOCAL_MARKDOWN_DIR, DEFAULT_PARENT_FOLDER_TOKEN

# 加载环境变量
load_dotenv()

def main():
    # 初始化客户端
    markdown_parser = MarkdownParser()
    feishu_client = FeishuClient()
    
    # 获取配置
    markdown_dir = LOCAL_MARKDOWN_DIR

    # 默认根文件夹
    root_folder_token = DEFAULT_PARENT_FOLDER_TOKEN
    
    if not markdown_dir or not os.path.exists(markdown_dir):
        print(f"请在.env文件中设置正确的LOCAL_MARKDOWN_DIR，并确保目录存在")
        return
        
    if os.getenv('FEISHU_APP_ID') == 'your_feishu_app_id' or os.getenv('FEISHU_APP_SECRET') == 'your_feishu_app_secret':
        print("请在.env文件中设置正确的FEISHU_APP_ID和FEISHU_APP_SECRET")
        return
    
    try:
        print(f"开始从本地Markdown文件迁移到飞书...")
        
        # 创建根文件夹
        # root_folder_name = "Markdown导入文档"
        # root_folder_token = feishu_client.create_folder(root_folder_name)
        # print(f"已创建根文件夹: {root_folder_name}")
        
        # 获取所有Markdown文件
        markdown_files = markdown_parser.get_markdown_files()
        print(f"找到{len(markdown_files)}个Markdown文件")
        
        # 创建文件夹映射，用于记录已创建的文件夹
        folder_mapping = {'': root_folder_token}
        
        # 处理每个Markdown文件
        for file_info in markdown_files:
            file_path = file_info['path']
            file_name = file_info['name']
            folder_path = file_info['folder']
            
            print(f"正在处理: {file_path}")
            
            # 确保目标文件夹存在
            parent_token = root_folder_token
            if folder_path:
                # 创建嵌套文件夹
                folder_parts = folder_path.split(os.sep)
                current_path = ''
                
                for part in folder_parts:
                    if not part:
                        continue
                        
                    current_path = os.path.join(current_path, part)
                    
                    if current_path not in folder_mapping:
                        # 创建新文件夹
                        parent = folder_mapping.get(os.path.dirname(current_path), root_folder_token)
                        folder_token = feishu_client.create_folder(part, parent)
                        folder_mapping[current_path] = folder_token
                        print(f"  创建文件夹: {current_path}")
                    
                parent_token = folder_mapping[current_path]
            
            # 解析Markdown文件
            blocks = markdown_parser.parse_markdown_file(file_path)
            
            # 转换内容
            # feishu_blocks = feishu_client._format_blocks_for_feishu(blocks)
            
            # 创建飞书文档
            result = feishu_client.create_document(file_name, parent_token)
            print(f"  文档创建成功: {file_name}")
            
        print(f"所有文档迁移完成！")
        
    except Exception as e:
        print(f"迁移过程中发生错误: {str(e)}")
    finally:
        # 清理临时文件
        temp_dir = "./temp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("已清理临时文件")

if __name__ == "__main__":
    main()
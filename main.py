import argparse
import os
import shutil
from dotenv import load_dotenv
from src.markdown_parser import MarkdownParser
from src.feishu_client import FeishuClient
from src.path_utils import normalize_config_path
from src.sync_state import SyncState
from config.config import LOCAL_MARKDOWN_DIR, DEFAULT_PARENT_FOLDER_TOKEN

# 加载环境变量
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="同步本地 Markdown 文件到飞书")
    parser.add_argument(
        "--mark-current-synced",
        action="store_true",
        help="只记录当前 Markdown 文件状态，不上传；用于首次启用定时同步前建立基线",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 获取配置
    markdown_dir = normalize_config_path(LOCAL_MARKDOWN_DIR)
    
    # 默认根文件夹
    root_folder_token = DEFAULT_PARENT_FOLDER_TOKEN
    
    if not markdown_dir or not os.path.exists(markdown_dir):
        print(f"请在.env文件中设置正确的LOCAL_MARKDOWN_DIR，并确保目录存在")
        return
        
    if os.getenv('FEISHU_APP_ID') == 'your_feishu_app_id' or os.getenv('FEISHU_APP_SECRET') == 'your_feishu_app_secret':
        print("请在.env文件中设置正确的FEISHU_APP_ID和FEISHU_APP_SECRET")
        return

    markdown_parser = MarkdownParser(markdown_dir)
    sync_state = SyncState()
    
    try:
        print(f"开始从本地Markdown文件同步到飞书...")
        
        # 获取所有Markdown文件
        markdown_files = markdown_parser.get_markdown_files()
        print(f"找到{len(markdown_files)}个Markdown文件")

        placeholder_files = markdown_parser.get_icloud_placeholder_files()
        if placeholder_files:
            print(f"发现{len(placeholder_files)}个iCloud占位文件，需先下载到本机后才能上传")
            for placeholder in placeholder_files[:10]:
                print(f"  未下载: {placeholder}")
            if len(placeholder_files) > 10:
                print(f"  还有{len(placeholder_files) - 10}个未显示")

        if args.mark_current_synced:
            for file_info in markdown_files:
                sync_state.mark_uploaded(file_info)
            sync_state.save()
            print(f"已将{len(markdown_files)}个Markdown文件标记为已同步，不执行上传")
            return

        changed_files = [file_info for file_info in markdown_files if sync_state.has_changed(file_info)]
        skipped_count = len(markdown_files) - len(changed_files)
        print(f"新增或变更{len(changed_files)}个，跳过未变化{skipped_count}个")

        if not changed_files:
            print("没有需要上传的Markdown文件")
            return

        # 初始化客户端
        feishu_client = FeishuClient()
        
        # 创建文件夹映射，用于记录已创建的文件夹
        folder_mapping = {'': root_folder_token}
        folder_mapping.update({
            os.path.normpath(path): token
            for path, token in sync_state.folders.items()
        })
        
        # 处理每个Markdown文件
        uploaded_count = 0
        for file_info in changed_files:
            file_path = file_info["path"]
            file_name = file_info["name"].rsplit(" ", 1)[0]
            folder_path = file_info["folder"]
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
                    
                    if current_path in folder_mapping:
                        folder_token = folder_mapping[current_path]
                    else:
                        parent = folder_mapping.get(os.path.dirname(current_path), root_folder_token)

                        folder_token = sync_state.get_folder_token(current_path)
                        if folder_token is None:
                            folder_token = feishu_client.get_child_folder_token(parent, part)

                        if folder_token is None:
                            folder_token = feishu_client.create_folder(part, parent)
                            print(f"  创建文件夹: {current_path}")
                            action = "created"
                        else:
                            action = "reuse"

                        if action != "created":
                            print(f"  复用文件夹: {current_path}")

                        if folder_token is None:
                            raise RuntimeError(f"无法获取文件夹 {current_path} 的 token")

                        folder_mapping[current_path] = folder_token
                        sync_state.mark_folder(current_path, folder_token)
                        sync_state.save()
                    
                parent_token = folder_mapping[current_path]

            # 上传markdown文件为飞书文档（有历史映射则覆盖旧文档）
            existing_doc_token = sync_state.get_doc_token(file_info)
            if not existing_doc_token:
                existing_doc_token = feishu_client.get_child_doc_token(parent_token, file_name)

            doc_token = feishu_client.import_md_to_docx(
                file_path,
                file_name,
                parent_token,
                existing_doc_token=existing_doc_token,
            )
            sync_state.mark_uploaded(file_info, doc_token=doc_token)
            sync_state.save()
            uploaded_count += 1
            
            print(f"  文档上传完成: {file_name}")
    
        print(f"同步完成：上传{uploaded_count}个，跳过{skipped_count}个")
        
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

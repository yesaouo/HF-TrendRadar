import os
import json
import time
import glob
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from hf_scraper import run_huggingface_data_pipeline
from ai_dataset_digest import AIAgent

def retry_with_delay(func, *args, retries=5, error_delay=60):
    for attempt in range(retries):
        try:
            return func(*args)
        except Exception as e:
            print(f"第 {attempt+1} 次嘗試時發生錯誤: {e}")
            if attempt < retries - 1:
                print(f"等待 {error_delay} 秒後重試...")
                time.sleep(error_delay)
            else:
                raise

def load_latest_json(sort_by):
    file_path = f"data/{sort_by}_*.json"
    files = glob.glob(file_path)

    if not files:
        print(f"沒有找到符合 {file_path} 的檔案。")
        return None
    else:
        latest_file = max(files, key=os.path.getmtime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            print(f"已開啟最新的檔案：{Path(latest_file).name}")
            return json.load(f)


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("請在 .env 檔案中設定 GEMINI_API_KEY")
agent = AIAgent(gemini_api_key=api_key)

NUM_DATASETS_TO_FETCH_PER_SORT = 30
sort_options = ["downloads", "likes", "lastModified"]

print("========================================================")
print(" Starting Hugging Face Data Pipeline for Multiple Sorts ")
print("========================================================")
start_time = time.time()

for sort_criteria in sort_options:
    run_huggingface_data_pipeline(sort_by_option=sort_criteria, limit_per_sort=NUM_DATASETS_TO_FETCH_PER_SORT)
    print("\n--------------------------------------------------------\n")

elapsed = time.time() - start_time
print("========================================================")
print(f" All Hugging Face Data Pipeline Runs Complete in {int(elapsed)}s")
print("========================================================")

output_path = "data/output.json"
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        prev_output = json.load(f)
else:
    prev_output = {}

downloads_data = load_latest_json('downloads')
try:
    if downloads_data:
        downloads_digest = retry_with_delay(agent.generate_downloads_digest, downloads_data)
        print("下載量數據摘要生成完成")
        print("等待30秒...")
        time.sleep(30)
    else:
        downloads_digest = prev_output.get("downloads_digest")
except Exception as e:
    print(f"下載量摘要生成失敗: {e}")
    downloads_digest = prev_output.get("downloads_digest")

likes_data = load_latest_json('likes')
try:
    if likes_data:
        likes_digest = retry_with_delay(agent.generate_likes_digest, likes_data)
        print("按讚數據摘要生成完成")
        print("等待30秒...")
        time.sleep(30)
    else:
        likes_digest = prev_output.get("likes_digest")
except Exception as e:
    print(f"按讚摘要生成失敗: {e}")
    likes_digest = prev_output.get("likes_digest")

last_modified_data = load_latest_json('lastModified')
try:
    if last_modified_data:
        last_modified_digest = retry_with_delay(agent.generate_lastModified_digest, last_modified_data)
        print("最近更新數據摘要生成完成")
    else:
        last_modified_digest = prev_output.get("last_modified_digest")
except Exception as e:
    print(f"最近更新摘要生成失敗: {e}")
    last_modified_digest = prev_output.get("last_modified_digest")

output = {
    "created_at": datetime.now().isoformat(),
    "downloads": downloads_data if downloads_data else prev_output.get("downloads"),
    "likes": likes_data if likes_data else prev_output.get("likes"),
    "last_modified": last_modified_data if last_modified_data else prev_output.get("last_modified"),
    "downloads_digest": downloads_digest,
    "likes_digest": likes_digest,
    "last_modified_digest": last_modified_digest
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

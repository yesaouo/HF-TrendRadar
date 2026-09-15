import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from hf_scraper import run_huggingface_data_pipeline
from ai_dataset_digest import AIAgent
import trend_history

def retry_with_delay(func, *args, retries=3, error_delay=30):
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

scraped = {}
for sort_criteria in sort_options:
    datasets = run_huggingface_data_pipeline(
        sort_by_option=sort_criteria,
        limit_per_sort=NUM_DATASETS_TO_FETCH_PER_SORT,
    )
    if datasets:
        scraped[sort_criteria] = datasets
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

history = trend_history.load_history()
if scraped:
    trend_history.append_snapshot(history, trend_history.build_snapshot(scraped))
    trend_history.save_history(history)
else:
    print("這次一份資料都沒爬到，不新增歷史快照。")

trending = trend_history.compute_trending(history)
if trending.get("available"):
    print(f"趨勢計算完成：近 {trending['window_days']} 天有 "
          f"{len(trending['items'])} 個資料集動能為正，"
          f"新進榜 {len(trending['entered'])}、掉出榜 {len(trending['exited'])}。")
else:
    print(f"趨勢暫時算不出來：{trending['reason']}（摘要會略過動能那一段）")

digest_times = dict(prev_output.get("digests_generated_at") or {})
run_time = datetime.now(timezone.utc).isoformat()

downloads_data = scraped.get("downloads")
try:
    if downloads_data:
        downloads_digest = retry_with_delay(agent.generate_downloads_digest, downloads_data, trending)
        digest_times["downloads"] = run_time
        print("下載量數據摘要生成完成")
        print("等待30秒...")
        time.sleep(30)
    else:
        downloads_digest = prev_output.get("downloads_digest")
except Exception as e:
    print(f"下載量摘要生成失敗: {e}")
    downloads_digest = prev_output.get("downloads_digest")

likes_data = scraped.get("likes")
try:
    if likes_data:
        likes_digest = retry_with_delay(agent.generate_likes_digest, likes_data, trending)
        digest_times["likes"] = run_time
        print("按讚數據摘要生成完成")
        print("等待30秒...")
        time.sleep(30)
    else:
        likes_digest = prev_output.get("likes_digest")
except Exception as e:
    print(f"按讚摘要生成失敗: {e}")
    likes_digest = prev_output.get("likes_digest")

last_modified_data = scraped.get("lastModified")
try:
    if last_modified_data:
        last_modified_digest = retry_with_delay(agent.generate_lastModified_digest, last_modified_data, trending)
        digest_times["last_modified"] = run_time
        print("最近更新數據摘要生成完成")
    else:
        last_modified_digest = prev_output.get("last_modified_digest")
except Exception as e:
    print(f"最近更新摘要生成失敗: {e}")
    last_modified_digest = prev_output.get("last_modified_digest")

output = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "downloads": downloads_data if downloads_data else prev_output.get("downloads"),
    "likes": likes_data if likes_data else prev_output.get("likes"),
    "last_modified": last_modified_data if last_modified_data else prev_output.get("last_modified"),
    "downloads_digest": downloads_digest,
    "likes_digest": likes_digest,
    "last_modified_digest": last_modified_digest,
    "digests_generated_at": digest_times,
    "trending": trending
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

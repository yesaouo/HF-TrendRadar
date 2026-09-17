import os
import json
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

import trend_history
from ai_dataset_digest import AIAgent
from hf_scraper import run_huggingface_data_pipeline

OUTPUT_PATH = "data/output.json"
NUM_DATASETS_TO_FETCH_PER_SORT = 30

DIGEST_JOBS = [
    ("downloads", "downloads", "generate_downloads_digest", 30),
    ("likes", "likes", "generate_likes_digest", 30),
    ("last_modified", "lastModified", "generate_lastModified_digest", 0),
]


def retry_with_delay(func, *args, retries=3, error_delay=30):
    for attempt in range(retries):
        try:
            return func(*args)
        except Exception as e:
            print(f"第 {attempt + 1} 次嘗試時發生錯誤: {e}")
            if attempt < retries - 1:
                print(f"等待 {error_delay} 秒後重試...")
                time.sleep(error_delay)
            else:
                raise


def load_prev_output(path=OUTPUT_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"警告：讀取 {path} 失敗（{e}），視為沒有舊資料。")
        return {}


def scrape_all():
    print("========================================================")
    print(" Starting Hugging Face Data Pipeline for Multiple Sorts ")
    print("========================================================")
    start_time = time.time()

    scraped = {}
    for _, sort_by, _, _ in DIGEST_JOBS:
        datasets = run_huggingface_data_pipeline(
            sort_by_option=sort_by,
            limit_per_sort=NUM_DATASETS_TO_FETCH_PER_SORT,
        )
        if datasets:
            scraped[sort_by] = datasets
        print("\n--------------------------------------------------------\n")

    print("========================================================")
    print(f" All Hugging Face Data Pipeline Runs Complete in {int(time.time() - start_time)}s")
    print("========================================================")
    return scraped


def update_history(scraped):
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
    return trending


def build_digests(agent, scraped, trending, prev_output, run_time):
    digests = {}
    generated_at = dict(prev_output.get("digests_generated_at") or {})

    for key, sort_by, method, cooldown in DIGEST_JOBS:
        datasets = scraped.get(sort_by)
        if not datasets:
            print(f"{key}：這次沒有爬到資料，沿用上一次的摘要。")
            digests[key] = prev_output.get(f"{key}_digest")
            continue
        try:
            digests[key] = retry_with_delay(getattr(agent, method), datasets, trending)
            generated_at[key] = run_time
            print(f"{key} 摘要生成完成")
            if cooldown:
                print(f"等待 {cooldown} 秒...")
                time.sleep(cooldown)
        except Exception as e:
            print(f"{key} 摘要生成失敗：{e}，沿用上一次的摘要。")
            digests[key] = prev_output.get(f"{key}_digest")

    return digests, generated_at


def build_output(scraped, prev_output, digests, generated_at, trending):
    output = {"created_at": datetime.now(timezone.utc).isoformat()}
    for key, sort_by, _, _ in DIGEST_JOBS:
        output[key] = scraped.get(sort_by) or prev_output.get(key)
    for key, _, _, _ in DIGEST_JOBS:
        output[f"{key}_digest"] = digests[key]
    output["digests_generated_at"] = generated_at
    output["trending"] = trending
    return output


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("請設定 GEMINI_API_KEY（本機放 .env，GitHub Actions 放 repository secret）")
    agent = AIAgent(gemini_api_key=api_key)

    scraped = scrape_all()
    prev_output = load_prev_output()
    trending = update_history(scraped)

    run_time = datetime.now(timezone.utc).isoformat()
    digests, generated_at = build_digests(agent, scraped, trending, prev_output, run_time)

    output = build_output(scraped, prev_output, digests, generated_at, trending)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"已寫入 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

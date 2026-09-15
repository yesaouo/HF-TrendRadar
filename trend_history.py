import json
import os
from datetime import datetime, timedelta, timezone

HISTORY_PATH = "data/history.json"

# 同一批資料重跑（手動觸發、補跑）時，間隔小於這個時數就覆蓋上一筆，避免歷史被灌爆
MIN_SNAPSHOT_INTERVAL_HOURS = 12

# 基準點比這個天數還舊就不算趨勢。中斷很久之後重啟時，只會產生看起來很厲害但毫無意義的數字。
MAX_BASELINE_AGE_DAYS = 45


# --- 小工具 ---

def parse_iso(value):
    """把 ISO 字串轉成帶時區的 datetime；失敗回 None。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _snapshot_sort_key(snapshot):
    return parse_iso(snapshot.get("date")) or datetime.min.replace(tzinfo=timezone.utc)


# --- 歷史檔讀寫 ---

def load_history(path=HISTORY_PATH):
    if not os.path.exists(path):
        return {"snapshots": []}
    try:
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"警告：讀取 {path} 失敗（{e}），改以空歷史重建。")
        return {"snapshots": []}
    if not isinstance(history, dict):
        return {"snapshots": []}
    history.setdefault("snapshots", [])
    return history


def save_history(history, path=HISTORY_PATH):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, separators=(",", ":"))
    print(f"歷史已寫入 {path}（共 {len(history['snapshots'])} 筆快照）")


def build_snapshot(datasets_by_sort, taken_at=None):
    """把幾份排行榜壓成一筆快照 {dataset_id: [downloads, likes]}。"""
    taken_at = taken_at or datetime.now(timezone.utc)
    metrics = {}
    for datasets in datasets_by_sort.values():
        for ds in datasets or []:
            ds_id = ds.get("id")
            if not ds_id:
                continue
            metrics[ds_id] = [ds.get("downloads") or 0, ds.get("likes") or 0]
    return {"date": taken_at.isoformat(), "metrics": metrics}


def append_snapshot(history, snapshot):
    """追加一筆快照；跟上一筆太近就直接取代它。"""
    snapshots = history.setdefault("snapshots", [])
    new_date = parse_iso(snapshot.get("date"))
    if snapshots and new_date:
        last_date = parse_iso(snapshots[-1].get("date"))
        if last_date and new_date - last_date < timedelta(hours=MIN_SNAPSHOT_INTERVAL_HOURS):
            print(f"距離上一筆快照不到 {MIN_SNAPSHOT_INTERVAL_HOURS} 小時，覆蓋上一筆而非新增。")
            snapshots[-1] = snapshot
            return history
    snapshots.append(snapshot)
    snapshots.sort(key=_snapshot_sort_key)
    return history


# --- 趨勢計算 ---

def _pick_baseline(snapshots, window_days):
    """挑一筆最接近 window_days 之前的快照當比較基準；歷史不夠久就用最舊的那筆。"""
    latest = parse_iso(snapshots[-1]["date"])
    target = latest - timedelta(days=window_days)
    return min(snapshots[:-1], key=lambda s: abs((parse_iso(s["date"]) - target).total_seconds()))


def _pct(delta, before):
    if not before:
        return None
    return round(delta / before * 100, 1)


def compute_trending(history, window_days=7, min_downloads=1000, top_n=30):
    """比較最新快照與約 window_days 前的快照，算出動能排行、新進榜與掉出榜。"""
    snapshots = [s for s in history.get("snapshots", []) if parse_iso(s.get("date"))]
    if len(snapshots) < 2:
        return {
            "available": False,
            "reason": "歷史快照還不到兩筆，要再跑一次才算得出趨勢。",
        }

    current = snapshots[-1]
    baseline = _pick_baseline(snapshots, window_days)
    current_at = parse_iso(current["date"])
    baseline_at = parse_iso(baseline["date"])
    elapsed_days = (current_at - baseline_at).total_seconds() / 86400
    if elapsed_days <= 0:
        return {"available": False, "reason": "找不到比最新快照更早的基準點。"}
    if elapsed_days > MAX_BASELINE_AGE_DAYS:
        return {
            "available": False,
            "reason": f"最接近的基準點在 {round(elapsed_days)} 天前，"
                      f"超過 {MAX_BASELINE_AGE_DAYS} 天上限。"
                      "再累積一次資料更新就會有近期的比較基準。",
        }

    current_metrics = current.get("metrics", {})
    baseline_metrics = baseline.get("metrics", {})

    items = []
    entered = []
    total_now = total_before = 0
    rising = falling = 0

    for ds_id, values in current_metrics.items():
        downloads, likes = (list(values) + [0, 0])[:2]
        before = baseline_metrics.get(ds_id)
        if before is None:
            entered.append(ds_id)
            continue
        before_downloads, before_likes = (list(before) + [0, 0])[:2]
        downloads_delta = downloads - before_downloads
        likes_delta = likes - before_likes

        total_now += downloads
        total_before += before_downloads
        if downloads_delta > 0:
            rising += 1
        elif downloads_delta < 0:
            falling += 1

        items.append({
            "id": ds_id,
            "downloads": downloads,
            "likes": likes,
            "downloads_delta": downloads_delta,
            "downloads_pct": _pct(downloads_delta, before_downloads),
            "likes_delta": likes_delta,
            "likes_pct": _pct(likes_delta, before_likes),
        })

    exited = [ds_id for ds_id in baseline_metrics if ds_id not in current_metrics]

    # 排行只收「本來就有一定量體、而且確實在成長」的，避免小基數製造假爆紅
    ranked = [
        item for item in items
        if item["downloads"] >= min_downloads
        and item["downloads_delta"] > 0
        and item["downloads_pct"] is not None
    ]
    ranked.sort(key=lambda item: item["downloads_pct"], reverse=True)

    return {
        "available": True,
        "window_days": round(elapsed_days, 1),
        "baseline_date": baseline["date"],
        "current_date": current["date"],
        "min_downloads": min_downloads,
        "items": ranked[:top_n],
        "entered": sorted(entered),
        "exited": sorted(exited),
        "totals": {
            "tracked": len(items),
            "rising": rising,
            "falling": falling,
            "downloads_now": total_now,
            "downloads_before": total_before,
            "downloads_pct": _pct(total_now - total_before, total_before),
        },
    }


# --- 本機除錯用：python trend_history.py ---

if __name__ == "__main__":
    history = load_history()
    result = compute_trending(history)
    if not result["available"]:
        print(result["reason"])
    else:
        print(f"比較區間：{result['baseline_date']} -> {result['current_date']}"
              f"（{result['window_days']} 天）")
        totals = result["totals"]
        print(f"追蹤 {totals['tracked']} 個資料集："
              f"{totals['rising']} 升 / {totals['falling']} 降，"
              f"新進榜 {len(result['entered'])}，掉出榜 {len(result['exited'])}")
        print("-" * 60)
        for i, item in enumerate(result["items"][:15], 1):
            print(f"{i:2}. {item['id'][:45]:45} "
                  f"{item['downloads_pct']:+8.1f}%  ({item['downloads_delta']:+,})")

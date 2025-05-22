import requests
import os
import json
from datetime import datetime, timezone
import time

# --- Configuration ---
BASE_API_URL = "https://huggingface.co/api/datasets"
VIEWER_API_URL = "https://datasets-server.huggingface.co/rows"
MODALITY_KEYWORDS = {
    "3d": "3D",
    "audio": "Audio",
    "geospatial": "Geospatial",
    "image": "Image",
    "tabular": "Tabular",
    "text": "Text",
    "timeseries": "Time-Series",
    "video": "Video"
}
REQUEST_HEADERS = {
    "User-Agent": "MyPythonScript/1.0 (fetching HF dataset info)"
}
# Delay between viewer API calls to be polite to the server
VIEWER_API_DELAY_SECONDS = 0.2

# --- Helper Functions ---

def format_to_iso8601(date_string):
    """Converts a date string to ISO8601 format (UTC)."""
    if not date_string:
        return None
    try:
        # Hugging Face dates are typically like "2022-11-10T10:06:17.000Z"
        # datetime.fromisoformat handles 'Z' correctly in Python 3.7+
        if date_string.endswith('Z'):
            dt_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else: # Try to parse if not ending with Z, assuming it might be naive
            dt_obj = datetime.fromisoformat(date_string)

        # Ensure it's UTC if it was naive
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        else:
            dt_obj = dt_obj.astimezone(timezone.utc)

        return dt_obj.isoformat()
    except ValueError:
        print(f"Warning: Could not parse date string: {date_string}")
        return date_string # Return original if parsing fails

# --- Main Data Fetching and Processing ---

def fetch_huggingface_datasets(sort_by="downloads", limit=100):
    """Fetches dataset list from Hugging Face API."""
    params = {"sort": sort_by, "limit": limit}
    print(f"Fetching datasets from {BASE_API_URL} (sort_by={sort_by}, limit={limit})")
    try:
        response = requests.get(BASE_API_URL, params=params, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dataset list for sort_by={sort_by}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for sort_by={sort_by}: {e}")
        return None

def fetch_dataset_viewer_sample(dataset_id_hf_format):
    """Fetches sample rows from the Dataset Viewer API."""
    if not dataset_id_hf_format:
        return []
    params = {
        "dataset": dataset_id_hf_format,
        "config": "default",
        "split": "train",
        "offset": 0,
        "length": 10
    }
    viewer_url = f"{VIEWER_API_URL}"
    # print(f"  Fetching viewer data for {dataset_id_hf_format} from {viewer_url} with params: {params}")
    time.sleep(VIEWER_API_DELAY_SECONDS) # Be polite
    try:
        response = requests.get(viewer_url, params=params, headers=REQUEST_HEADERS, timeout=20)
        if response.status_code == 200:
            return response.json().get("rows", [])
        elif response.status_code == 404:
            # print(f"  Viewer data not found (404) for {dataset_id_hf_format} with config 'default' and split 'train'.")
            return [] # No viewer data or specific config/split not found
        else:
            response.raise_for_status() # For other errors
            return []
    except requests.exceptions.RequestException as e:
        # print(f"  Error fetching viewer data for {dataset_id_hf_format}: {e}")
        return []
    except json.JSONDecodeError as e:
        # print(f"  Error decoding JSON from viewer API for {dataset_id_hf_format}: {e}")
        return []

def process_datasets(datasets_raw):
    """Processes raw dataset data, cleans fields, and fetches viewer samples."""
    processed_datasets = []
    if not datasets_raw:
        return processed_datasets

    for i, ds_data in enumerate(datasets_raw):
        print(f"Processing dataset {i+1}/{len(datasets_raw)}: {ds_data.get('id', 'N/A')}")

        # Create a copy to modify
        processed_ds = ds_data.copy()

        # 1. Unify date formats
        processed_ds["createdAt"] = format_to_iso8601(ds_data.get("createdAt"))
        processed_ds["lastModified"] = format_to_iso8601(ds_data.get("lastModified"))

        # 2. Fetch viewer data
        processed_ds["viewer_sample_rows"] = fetch_dataset_viewer_sample(ds_data.get("id"))

        # 3. Identify modalities from tags
        processed_ds["modalities"] = []
        tags = ds_data.get("tags", [])
        if tags:
            for tag in tags:
                if tag.startswith("modality:"):
                    keyword = tag.split(":")[1]
                    modality_name = MODALITY_KEYWORDS.get(keyword)
                    if modality_name:
                        processed_ds["modalities"].append(modality_name)
        # if not processed_ds["modalities"] and tags:
        #     print(f"  No primary modality identified from tags: {tags[:5]}")

        processed_datasets.append(processed_ds)
    return processed_datasets

def group_by_modality(datasets):
    """Groups datasets by their identified modalities."""
    grouped = {}
    for ds in datasets:
        modalities = ds.get("modalities", [])
        if not modalities:
            group_name = "Other/Unknown"
            if group_name not in grouped:
                grouped[group_name] = []
            grouped[group_name].append(ds)
        else:
            for modality in modalities:
                if modality not in grouped:
                    grouped[modality] = []
                grouped[modality].append(ds)
    return grouped

def run_huggingface_data_pipeline(sort_by_option, limit_per_sort):
    """Runs the full data fetching, processing, and grouping pipeline for a given sort_by option."""
    print(f"\n--- Starting Hugging Face dataset processing for sort_by='{sort_by_option}' ---")

    # 資料擷取 (Part 1: Main list)
    raw_datasets = fetch_huggingface_datasets(sort_by=sort_by_option, limit=limit_per_sort)

    if raw_datasets:
        # 資料擷取 (Part 2: Viewer API) & 資料預處理
        print(f"\n--- Starting dataset preprocessing for {sort_by_option} ---")
        all_processed_data = process_datasets(raw_datasets)
        print(f"--- Finished dataset preprocessing for {sort_by_option} ---")

        # 分類標籤 (Grouping)
        grouped_datasets = group_by_modality(all_processed_data)

        # # --- Output Results ---
        # print("\n--- Datasets Grouped by Modality ---")
        # for modality, datasets_in_group in grouped_datasets.items():
        #     print(f"\n modality: {modality} ({len(datasets_in_group)} datasets)")
        #     # Print first 3 for brevity
        #     for i, ds_item in enumerate(datasets_in_group[:3]):
        #         print(f"  - {ds_item.get('id')} (Likes: {ds_item.get('likes', 0)}, Downloads: {ds_item.get('downloads',0)})")
        #     if len(datasets_in_group) > 3:
        #         print(f"  ... and {len(datasets_in_group) - 3} more.")

        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_filename = os.path.join("data", f"{sort_by_option}_{timestamp}.json")
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(all_processed_data, f, indent=2, ensure_ascii=False)
            print(f"\nFull processed data for '{sort_by_option}' saved to {output_filename}")
        except IOError as e:
            print(f"Error saving data to file {output_filename}: {e}")
    else:
        print(f"Could not retrieve initial dataset list for sort_by='{sort_by_option}'. Skipping this run.")

    print(f"\n--- Processing complete for sort_by='{sort_by_option}' ---")

# --- Main Execution ---
if __name__ == "__main__":
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
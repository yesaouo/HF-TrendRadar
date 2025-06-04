# HF-TrendRadar: HuggingFace Dataset 趨勢雷達系統

HF-TrendRadar 是一個自動化系統，旨在追蹤 Hugging Face 平台上熱門、受歡迎以及近期活躍的資料集。它定期爬取 Hugging Face API，對資料集進行分類和處理，並利用 Google Gemini AI 模型產生趨勢洞察報告。前端介面讓使用者可以輕鬆瀏覽不同類別的資料集、查看詳細資訊，並與 AI 助理互動以獲取特定資料集的更多見解。

![螢幕擷取畫面 2025-06-04 135534](https://github.com/user-attachments/assets/e1398558-59ec-4052-b1af-ebb115321872)

## ✨ 主要功能

*   **自動化資料擷取**: 定期從 Hugging Face API 獲取按「下載量」、「按讚數」和「最後修改日期」排序的頂尖資料集。
*   **AI 趨勢摘要**:
    *   使用 Google Gemini 模型分析各類別的熱門資料集。
    *   產生「高下載量數據洞察報告」、「高人氣數據洞察報告」和「新興與活躍數據洞察報告」。
    *   報告內容包含主要領域分析、模態分佈、趨勢總結、研究建議和總體陳述。
    ![螢幕擷取畫面 2025-06-04 140051](https://github.com/user-attachments/assets/34b62340-e232-402a-80be-8b33e2079aea)
*   **互動式前端介面**:
    *   清晰的標籤頁導航 (Downloads, Likes, Last Modified)。
    *   美觀的資料集卡片展示，包含 ID、簡短描述、作者、下載/按讚數、最後修改日期及資料模態。
    *   卡片顏色根據資料模態動態調整，提供視覺提示。
    ![螢幕擷取畫面 2025-06-04 140948](https://github.com/user-attachments/assets/5a5648aa-53ed-433d-9d0b-e92fc8e34dc1)
    *   點擊卡片可開啟詳細資訊彈窗，包含完整描述、標籤、創建/修改時間和 Hugging Face 原始連結。
    ![螢幕擷取畫面 2025-06-04 141730](https://github.com/user-attachments/assets/9b12a9ae-684f-497c-b4fd-d7fee4268391)
*   **資料集 AI 助理**:
    *   在資料集詳細資訊彈窗中，提供「AI Assistant」按鈕。
    *   開啟聊天視窗，使用者可以針對當前資料集向 Gemini 模型提問。
    *   聊天記錄會被保存並顯示在介面上。
    ![螢幕擷取畫面 2025-06-04 221120](https://github.com/user-attachments/assets/518a9c7f-2393-4477-a44c-f04e0ffc8d9a)
*   **安全 API Key 管理**: Gemini API Key 儲存在瀏覽器的 localStorage，不會明文顯示。
*   **資料持久化與版本控制**:
    *   爬取的原始資料和 AI 生成的摘要會儲存為 JSON 檔案 (`data/output.json`)。
    *   透過 `run_and_push.sh` 腳本自動將更新後的 `output.json` 推送到 GitHub。
*   **定期自動更新**: 使用 cron job 定期執行資料抓取、分析和推送流程。

## ⚙️ 系統架構

1.  **資料抓取 (`hf_scraper.py`)**:
    *   使用 `requests` 庫呼叫 Hugging Face API (`/api/datasets`)，獲取按不同標準排序的資料集列表。
    *   針對每個資料集，嘗試呼叫 Dataset Viewer API (`/rows`) 獲取樣本資料。
    *   處理原始資料，統一日期格式，從標籤中提取資料模態。
    *   將每個排序類別的處理後資料儲存為帶時間戳的 JSON 檔案 (例如 `data/downloads_YYYYMMDDTHHMMSSZ.json`)。

2.  **AI 分析 (`ai_dataset_digest.py`)**:
    *   `AIAgent` 類別使用提供的 Gemini API Key 初始化。
    *   針對每個排序類別 (Downloads, Likes, Last Modified)，讀取最新的 JSON 資料。
    *   根據預設的系統提示詞 (System Prompt) 和資料集資訊，格式化使用者提示詞 (User Prompt)。
    *   呼叫 Gemini API (透過 OpenAI 相容的 `base_url`) 生成趨勢摘要報告。
    *   包含重試機制以應對 API 呼叫失敗。

3.  **主流程控制與輸出 (`main.py`)**:
    *   載入 `.env` 中的 Gemini API Key。
    *   依次執行 `hf_scraper.py` 的資料抓取流程，針對 Downloads, Likes, Last Modified。
    *   呼叫 `AIAgent` 生成三種趨勢摘要。
    *   整合所有資料 (最新抓取的各類別資料集、AI 生成的摘要) 以及當前時間戳，寫入 `data/output.json`。
    *   若爬取或摘要生成失敗，會嘗試使用 `output.json` 中已有的舊資料。

4.  **前端展示 (`index.html`)**:
    *   純 HTML, CSS, JavaScript 實現，使用 `marked.min.js` 渲染 Markdown 格式的 AI 摘要。
    *   啟動時從 `data/output.json` 載入資料。
    *   動態渲染標籤頁、資料集卡片、摘要報告。
    *   處理使用者互動：切換標籤頁、打開資料集詳情彈窗、打開 AI 助理聊天視窗。
    *   AI 助理聊天功能直接呼叫 Google Gemini API (`generativelanguage.googleapis.com`)。

5.  **自動化 (`run_and_push.sh` & Cron)**:
    *   Shell 腳本 `run_and_push.sh` 負責：
        1.  切換到專案目錄。
        2.  執行 `main.py`。
        3.  將更新後的 `data/output.json` 加入 Git stage。
        4.  提交 Commit (包含日期時間)。
        5.  推送到 GitHub `main` 分支。
    *   Cron Job 設定為定期 (例如每週二和週五的午夜) 執行此腳本。

![Editor _ Mermaid Chart-2025-06-04-163003](https://github.com/user-attachments/assets/9eb5c46a-65b8-419a-b0c9-2cd44a9967a0)

## 🛠️ 技術堆疊

*   **後端**: Python 3
    *   `requests`: HTTP 請求
    *   `python-dotenv`: 環境變數管理
    *   `openai` (SDK for Gemini): AI 模型互動 (使用自訂 `base_url`)
*   **前端**:
    *   HTML5
    *   CSS3
    *   Vanilla JavaScript (ES6+)
    *   `marked.js`: Markdown 渲染
*   **AI 模型**: Google Gemini 2.0 Flash (透過其 OpenAI 相容 API 端點)
*   **資料儲存**: JSON 檔案
*   **自動化**: Bash, Cron
*   **版本控制 & 部署**: Git, GitHub, GitHub Pages

## 🚀 安裝與設定

1.  **複製儲存庫**:
    ```bash
    git clone https://github.com/yesaouo/HF-TrendRadar.git
    cd HF-TrendRadar
    ```

2.  **設定環境變數**:
    *   創建 `.env` 檔案。
    *   在 `.env` 檔案中加入您的 Google Gemini API Key:
        ```
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        ```
    *   確保您已在 Google AI Studio 中啟用 Gemini API 並獲取了 API 金鑰。

3.  **安裝 Python 依賴**:
    (假設您已安裝 Python 和 pip)
    ```bash
    pip install requests python-dotenv openai
    ```
    *注意: `openai` 庫用於與 Gemini API 的 OpenAI 相容端點互動。*

4.  **首次執行 (手動產生資料)**:
    ```bash
    python main.py
    ```
    這將會抓取資料、生成 AI 摘要，並在 `data/` 目錄下創建 `output.json`。

5.  **本地預覽前端**:
    *   由於 `index.html` 使用 `fetch` 從相對路徑載入 `data/output.json`，直接用瀏覽器打開本地檔案可能會遇到 CORS 問題。
    *   建議使用一個簡單的本地 HTTP 伺服器來預覽：
        ```bash
        python -m http.server
        ```
        然後在瀏覽器中打開 `http://localhost:8000` (或其他顯示的端口號)。

## 📖 使用說明

1.  **瀏覽網站**: 訪問部署後的 GitHub Pages 網址 (或本地預覽網址)。
2.  **輸入 API Key (可選但建議)**:
    *   在頁面頂部的 "Gemini API Key" 輸入框中輸入您的 Gemini API 金鑰。
    *   點擊 "Save Key"。此金鑰將儲存在瀏覽器的 localStorage，用於啟用資料集 AI 助理功能。若不輸入，AI 助理功能將不可用，但仍可瀏覽資料和 AI 生成的趨勢摘要。
3.  **瀏覽趨勢**:
    *   點擊 "Downloads", "Likes", 或 "Last Modified" 標籤頁來查看不同排序標準下的資料集。
    *   每個標籤頁下方會顯示對應的 AI 生成趨勢摘要報告。
4.  **查看資料集詳情**:
    *   點擊任一資料集卡片。
    *   彈窗將顯示該資料集的詳細資訊，包括完整描述、標籤、Hugging Face 連結等。
5.  **使用 AI 助理**:
    *   在資料集詳情彈窗中，點擊 "AI Assistant" 按鈕 (前提是已保存 Gemini API Key)。
    *   在聊天視窗中，針對當前資料集向 AI 提問 (例如："這個資料集適合哪些應用？"，"請總結一下這個資料集的特點。")。
    *   點擊 "Send" 或按 Enter 發送訊息。AI 的回覆將顯示在聊天記錄中。

## ⚙️ 自動化 (Cron Job)

為了保持資料的時效性，系統配置了 cron job 定期執行資料更新和分析流程。

**Cron Job 設定範例**:

```cron
0 0 * * 2,5 /home/yesaouo/HF-TrendRadar/run_and_push.sh >> /home/yesaouo/HF-TrendRadar/cron.log 2>&1
```

*   此設定表示：每週二和週五的午夜 (00:00) 執行 `run_and_push.sh` 腳本。
*   `>> /home/yesaouo/HF-TrendRadar/cron.log 2>&1` 將標準輸出和錯誤輸出都附加到日誌檔案。
*   **請根據您的伺服器環境和用戶名修改路徑。**
*   記得給 `run_and_push.sh` 執行權限: `chmod +x run_and_push.sh`

## 💡 未來可能的增強

*   **更細緻的資料篩選**: 允許使用者根據特定標籤、模態或任務類型篩選資料集。
*   **趨勢視覺化**: 使用圖表展示下載量、按讚數隨時間的變化趨勢。
*   **使用者自訂追蹤**: 允許使用者儲存感興趣的資料集或設定特定關鍵字的追蹤。
*   **更深入的 AI 分析**: 例如，比較不同資料集、識別特定領域的潛力等。
*   **錯誤通知**: 當自動化腳本執行失敗時，發送郵件或 Slack 通知。

## 📄 授權

本專案採用 [MIT License](LICENSE) 授權。

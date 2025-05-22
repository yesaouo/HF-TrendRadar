import os
from openai import OpenAI

class AIAgent:
    def __init__(self, gemini_api_key):
        self.api_key = gemini_api_key
        self.model = "gemini-2.0-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self.system_prompt_downloads = """
            您是一位 AI 資料策展人。您的任務是分析「下載量最高」的資料集，識別其趨勢，並為用戶推薦潛在的研究方向。
        """
        self.prompt_template_downloads = """
            這是一個目前在「下載量」方面名列前茅的資料集列表：
            {top_downloads_dataset_info}

            請透過以下步驟產生一份「高下載量數據洞察報告」：
            1.  **主要領域分析**：從這份列表中，辨識出下載量最高的資料集主要集中在哪些學術領域或應用主題？（例如：自然語言處理、電腦視覺、推薦系統、醫療影像、金融科技等）。請列出至少3-5個主要領域。
            2.  **模態分佈**：這些高下載量的資料集主要包含哪些資料模態（modalities）？（例如：文本、圖像、表格數據、時間序列、音訊、影片等）。是否有特定模態的資料集下載量特別突出？
            3.  **趨勢總結**：綜合以上分析，目前在資料集下載方面，哪些類型的數據最受歡迎？是否存在某些新興或持續熱門的主題？
            4.  **研究建議**：根據這些高下載量的資料集特性，您可以推薦用戶關注或投入哪些具體的研究方向或專案？（例如：若圖像資料集多，可建議圖像生成、物件偵測研究；若NLP資料集多，可建議文本分類、大型語言模型微調等）。請提供2-3個具體的建議。
            5.  **總體陳述**：最後，用一個簡短的總體陳述總結，為什麼這些高下載量的數據類型「正夯」，以及它們對研究社群的價值。
        """
        self.system_prompt_likes = """
            您是一位 AI 資料策展人。您的任務是分析「按讚數最高」的資料集，洞察社群偏好，並為用戶推薦潛在的研究方向。
        """
        self.prompt_template_likes = """
            這是一個目前在「按讚數」方面名列前茅的資料集列表：
            {top_likes_dataset_info}

            請透過以下步驟產生一份「高人氣數據洞察報告」：
            1.  **主要領域分析**：從這份列表中，辨識出按讚數最高的資料集主要集中在哪些學術領域或應用主題？這些主題是否反映了當前的研究熱點或社會關注點？
            2.  **模態分佈**：這些高按讚數的資料集主要包含哪些資料模態？是否有特定模態的資料集更容易獲得社群的喜愛？
            3.  **趨勢總結**：綜合以上分析，目前在資料集按讚方面，哪些類型的數據最受社群青睞？它們通常具備哪些特質（例如：新穎性、實用性、趣味性、高質量）？
            4.  **研究建議**：根據這些高人氣資料集的特性，您可以推薦用戶關注或投入哪些能引起社群共鳴或具有較高影響潛力的研究方向或專案？請提供2-3個具體的建議。
            5.  **總體陳述**：最後，用一個簡短的總體陳述總結，為什麼這些高按讚數的數據類型「備受追捧」，以及它們對研究社群的啟示。
        """
        self.system_prompt_lastModified = """
            您是一位 AI 資料策展人。您的任務是分析「最近更新」的資料集，識別新興趨勢與活躍的數據領域，並為用戶推薦前瞻性的研究方向。
        """
        self.prompt_template_lastModified = """
            這是一個目前在「最後修改日期」方面名列前茅（即最新更新）的資料集列表：
            {top_lastModified_dataset_info}

            請透過以下步驟產生一份「新興與活躍數據洞察報告」：
            1.  **主要領域分析**：從這份列表中，辨識出最近頻繁更新或新發布的資料集主要集中在哪些學術領域或應用主題？這是否暗示了新的研究熱點或數據收集重點的轉移？
            2.  **模態分佈**：這些近期更新的資料集主要包含哪些資料模態？是否有特定模態的數據正在被積極擴充或有新的類型出現？
            3.  **趨勢總結**：綜合以上分析，目前哪些類型的數據展現出高度的「時效性」或「活躍度」？它們可能反映了哪些技術進展或社會需求的變化？
            4.  **研究建議**：根據這些近期活躍的資料集特性，您可以推薦用戶關注哪些可能引領未來趨勢的「新興研究方向」或利用這些最新數據進行哪些探索性專案？請提供2-3個具體的建議。
            5.  **總體陳述**：最後，用一個簡短的總體陳述總結，為什麼關注這些「近期活躍」的數據類型對研究者保持前瞻性至關重要。
        """

        os.environ["OPENAI_API_KEY"] = self.api_key
        self.client = OpenAI(
            base_url=self.base_url
        )

    def generate_downloads_digest(self, top_downloads):
        dataset_info_string = ""
        if not top_downloads:
            dataset_info_string = "目前沒有可分析的高下載量資料集。\n"
        else:
            for dataset in top_downloads:
                description = dataset.get("description", "無描述").replace("\n", " ")
                dataset_info_string += f"""
                    資料集: {dataset.get("id")}, 最後修改: {dataset.get("lastModified", "N/A")}
                    下載數: {dataset.get("downloads", 0)}, 按讚數: {dataset.get("likes", 0)}
                    描述: {description}
                    --------------------
                """
        final_prompt = self.prompt_template_downloads.format(top_downloads_dataset_info=dataset_info_string.strip())
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt_downloads},
                {"role": "user", "content": final_prompt},
            ]
        )
        return response.choices[0].message.content
    
    def generate_likes_digest(self, top_likes):
        dataset_info_string = ""
        if not top_likes:
            dataset_info_string = "目前沒有可分析的高按讚數資料集。\n"
        else:
            for dataset in top_likes:
                description = dataset.get("description", "無描述").replace("\n", " ")
                dataset_info_string += f"""
                    資料集: {dataset.get("id")}, 最後修改: {dataset.get("lastModified", "N/A")}
                    下載數: {dataset.get("downloads", 0)}, 按讚數: {dataset.get("likes", 0)}
                    描述: {description}
                    --------------------
                """
        final_prompt = self.prompt_template_likes.format(top_likes_dataset_info=dataset_info_string.strip())
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt_likes},
                {"role": "user", "content": final_prompt},
            ]
        )
        return response.choices[0].message.content
    
    def generate_lastModified_digest(self, top_lastModified):
        dataset_info_string = ""
        if not top_lastModified:
            dataset_info_string = "目前沒有可分析的近期更新資料集。\n"
        else:
            for dataset in top_lastModified:
                description = dataset.get("description", "無描述").replace("\n", " ")
                dataset_info_string += f"""
                    資料集: {dataset.get("id")}, 最後修改: {dataset.get("lastModified", "N/A")}
                    下載數: {dataset.get("downloads", 0)}, 按讚數: {dataset.get("likes", 0)}
                    描述: {description}
                    --------------------
                """
        final_prompt = self.prompt_template_lastModified.format(top_lastModified_dataset_info=dataset_info_string.strip())
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt_lastModified},
                {"role": "user", "content": final_prompt},
            ]
        )
        return response.choices[0].message.content

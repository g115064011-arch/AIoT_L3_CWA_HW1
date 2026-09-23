# 台灣天氣預報 Web App

## 專案目的

串接中央氣象署（CWA）開放資料平台 API，取得台灣各縣市天氣預報資料，並透過 Streamlit 建立互動式網頁儀表板，搭配地圖視覺化呈現天氣資訊。

> 🚧 本專案目前為初始架構階段，功能持續開發中。

---

## 使用技術

| 技術 | 用途 |
|------|------|
| Python | 主要程式語言 |
| Requests | 呼叫 CWA Open Data API |
| pandas | 資料處理與分析 |
| SQLite | 本地資料儲存 |
| Streamlit | 網頁介面與儀表板 |
| Folium + streamlit-folium | 地圖視覺化 |
| python-dotenv | 管理環境變數（API 金鑰） |

---

## 專案檔案結構

```
AIoT_L3_CWA_HW1/
├── app.py            # 應用程式入口點
├── weather_api.py    # CWA API 資料擷取模組（待實作）
├── database.py       # SQLite 資料庫操作模組（待實作）
├── requirements.txt  # Python 套件需求清單
├── .env              # 環境變數（API 金鑰，不納入版本控制）
├── .gitignore        # Git 忽略規則
├── README.md         # 專案說明文件
└── data/             # SQLite 資料庫存放目錄
```

---

## 安裝方式

1. 複製此專案：
   ```bash
   git clone <your-repo-url>
   cd AIoT_L3_CWA_HW1
   ```

2. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```

3. 在 `.env` 檔案中填入你的 CWA API 金鑰：
   ```
   CWA_API_KEY=你的金鑰
   ```

---

## 執行方式

```bash
python app.py
```

預期輸出：
```
Taiwan Weather Forecast
```

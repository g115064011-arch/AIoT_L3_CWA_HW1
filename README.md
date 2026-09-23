# 台灣天氣預報 Web App

# 🌤️ AIoT_L3_CWA_HW1

## 專案目的

串接中央氣象署（CWA）開放資料平台 API，取得台灣各縣市天氣預報資料，並透過 Streamlit 建立互動式網頁儀表板，搭配地圖視覺化呈現天氣資訊。

> 用 Python × CWA API × SQLite × Streamlit  
> 打造一個可以查天氣、看溫度趨勢、瀏覽台灣天氣地圖的小型 Web App ☀️🌧️🗺️

---

## ✨ 專案介紹

本專案使用中央氣象署（CWA）開放資料 API 取得台灣天氣預報資料，  
透過 Python 解析 JSON，並將資料儲存至 SQLite 資料庫中。

最後再利用 Streamlit 建立互動式網頁介面，讓使用者可以：

- 選擇不同縣市
- 查看天氣預報資料
- 比較最高溫與最低溫
- 查看溫度趨勢折線圖
- 使用互動式台灣地圖瀏覽各地天氣資訊

---

## 🌈 主要功能

目前已完成：

- ☁️ 從 CWA Open Data API 取得天氣資料
- 📦 解析 JSON 格式資料
- 🏙️ 取得台灣 22 縣市天氣資訊
- 🌡️ 擷取 MinT / MaxT
- 🌤️ 擷取天氣現象 Wx
- 🕒 擷取預報開始與結束時間
- 🗃️ 使用 SQLite 儲存資料
- 🚫 避免重複資料寫入
- 💻 使用 Streamlit 建立 Web App
- 🔽 縣市下拉選單
- 📋 天氣預報資料表
- 📈 最低溫 / 最高溫趨勢圖
- 🗺️ Folium 台灣互動式天氣地圖
- ⏰ 可選擇不同預報時段
- 🔄 可重新從 CWA API 更新資料

---

## 🔄 Workflow

本專案的資料處理流程如下：

```text
CWA Open Data API
        ↓
取得 JSON 天氣資料
        ↓
weather_api.py
解析 locationName / Wx / MinT / MaxT / startTime / endTime
        ↓
database.py
將整理後的資料寫入 SQLite
        ↓
SQL 查詢天氣資料
        ↓
app.py
使用 Streamlit 建立 Web App
        ↓
顯示：
📋 天氣預報表格
📈 MinT / MaxT 溫度趨勢圖
🗺️ 台灣互動式天氣地圖
⏰ 預報時段選擇
```
---

## 🛠️ 使用技術

- Python
- CWA Open Data API
- JSON
- Requests
- pandas
- SQLite
- SQL
- Streamlit
- Folium
- streamlit-folium
- python-dotenv
- Git
- GitHub

---

## 📁 專案結構

```text
AIoT_L3_CWA_HW1/
│
├── app.py
├── weather_api.py
├── database.py
├── requirements.txt
├── .gitignore
├── .env
├── README.md
│
└── data/
    └── weather.db
```
# 🏭 Water Guardian++  
### AI-Powered Cooling System Water Quality Monitor for Data Centers  

Water Guardian++ is an end-to-end environmental monitoring system designed for **data center cooling infrastructure**.  
It continuously tracks **Total Dissolved Solids (TDS)** and **temperature** in cooling loops to detect scaling, corrosion, or overheating — before costly downtime occurs.

---

## 🌐 Overview

The system integrates:

- **Arduino sensors** (for real-time water quality data)  
- **FastAPI backend** (`main_complete.py`) — handles storage, threshold detection, and AI analysis  
- **Flask frontend** (`servesite.py` + `frontend_dashboard.html`) — displays live readings and AI insights  
- **Email/SMS notifications** (`arduinowithnotifs.py`) — sends alerts on unsafe readings  
- **AI diagnostics** using **Google Gemini** for root-cause analysis and actionable recommendations  

---

## 🧠 Why We Used an External IP Instead of Localhost

During deployment and testing, the **Flask frontend** and **FastAPI backend** could not coexist cleanly on the same host using `localhost`.  
To resolve cross-origin and binding issues, the dashboard (`frontend_dashboard.html`) was configured to point directly to the **FastAPI server’s LAN IP** instead of `localhost`.

> ✅ **Configured backend base URL:** `http://192.168.137.165:8000`

This allows the frontend to access API routes such as:
- `/sensor_data`
- `/readings/latest`
- `/readings/history`
- `/analyses/recent`
- `/stats`

---

## ⚙️ Components

| File | Description |
|------|--------------|
| **main_complete.py** | FastAPI backend handling sensor data ingestion, threshold logic, AI analysis (Google Gemini), and SQLite persistence. |
| **servesite.py** | Flask app serving the `frontend_dashboard.html` interface. |
| **frontend_dashboard.html** | Web dashboard that fetches data from `http://192.168.137.165:8000` for visualization. |
| **arduinowithnotifs.py** | Serial listener reading Arduino JSON data, forwarding it to the backend, and sending email/SMS alerts for unsafe readings. |
| **cooling_system.db** | SQLite database storing sensor readings and AI analysis results. |
| **water_guardian.db** | Legacy/archival database — not used by the current system. |
| **.env** | Contains your `GEMINI_API_KEY` for AI integration. |

---

## 🧱 Database Schema

**`cooling_system.db`** (auto-created by FastAPI) contains:

- `readings` — sensor data (TDS, temperature, safe/unsafe flags)  
- `analyses` — AI responses, recommendations, and performance stats  

---

## 🚀 Getting Started

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Set Up Environment
Create a `.env` file:
```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 3️⃣ Start Backend (FastAPI)
```bash
python3 main_complete.py
```
- API runs at: [http://192.168.137.165:8000](http://192.168.137.165:8000)
- Docs available at: [http://192.168.137.165:8000/docs](http://192.168.137.165:8000/docs)

### 4️⃣ Start Frontend (Flask)
```bash
python3 servesite.py
```
- Dashboard at: [http://localhost:8080](http://localhost:8080)

*(Ensure the dashboard HTML points to `http://192.168.137.165:8000` for API calls.)*

### 5️⃣ Start Arduino Listener
```bash
python3 arduinowithnotifs.py
```

---

## 🧠 Example AI Output

```text
IMPACT:
Potential scale formation detected — could reduce cooling efficiency and raise rack temperatures.

ROOT CAUSE:
High TDS levels indicate excessive mineral concentration from evaporation losses.

ACTIONS:
1. Flush and replace cooling water within 24 hours.
2. Inspect and clean condenser heat exchanger.
3. Calibrate conductivity sensors to ensure accuracy.
```

---

## 📈 Key Features

- 🌊 Real-time monitoring of TDS & temperature  
- ⚙️ Automatic threshold detection (per ASHRAE standards)  
- 🤖 AI analysis triggered only when TDS > 1000 ppm  
- 📲 SMS/email alerts for unsafe readings  
- 💾 Persistent local storage with SQLite  
- 🧩 REST API for integration and dashboards  
- 💡 Estimated downtime prevention analytics  

---

## 🔒 Notes & Troubleshooting

- If the dashboard doesn’t load data, confirm that:
  - The backend is accessible via the **same IP** defined in your HTML.  
  - The FastAPI app is running on port `8000`.  
  - CORS is enabled (it is, by default in `main_complete.py`).  
- To clear all data:
  ```bash
  curl -X DELETE http://192.168.137.165:8000/data/clear
  ```

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

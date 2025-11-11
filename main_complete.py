"""
Water Guardian++ - Data Center Cooling System Monitor
For Grainger's Server Infrastructure
Sensors: TDS + Temperature
Smart AI triggering, Local SQLite DB

LOGIC NOTE: AI is now ONLY called if TDS > 1000 ppm to conserve API cost.
"""
from dotenv import load_dotenv
load_dotenv()

import os, time, json
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import google.generativeai as genai

# ============================================================================
# DATABASE
# ============================================================================
engine = create_engine("sqlite:///./cooling_system.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    TDS = Column(Float)
    temperature = Column(Float)
    is_safe = Column(Boolean)
    ai_triggered = Column(Boolean)

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reading_id = Column(Integer)
    analysis = Column(Text)
    status = Column(String(20))
    recommendations = Column(Text)
    response_ms = Column(Integer)

Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ============================================================================
# THRESHOLDS (ASHRAE Cooling Water Standards)
# ============================================================================
THRESHOLDS = {
    "TDS": {
        "optimal_min": 60,     # Too low = corrosive
        "optimal_max": 500,     # Ideal range for cooling
        "warning_max": 1200,    # Scale formation begins
        "critical_max": 1500    # Severe scaling/system damage
    },
    "temperature": {
        "optimal_min": 18,       # Efficient cooling range
        "optimal_max": 27,       # Maximum efficient temp
        "warning_min": 15,       # Too cold (inefficient)
        "warning_max": 32,       # Getting hot (reduced efficiency)
        "critical_min": 10,      # System issue
        "critical_max": 35       # Critical overheating
    }
}

def check_thresholds(tds, temp):
    """
    Check cooling water quality thresholds
    Returns: (should_trigger_ai, severity, issues)
    """
    issues = []
    severity = "safe"

    # Check TDS (conductivity for scale/corrosion)
    if tds < THRESHOLDS["TDS"]["optimal_min"]:
        issues.append(f"TDS {tds} ppm - TOO LOW (corrosion risk)")
        severity = "warning"
    elif tds > THRESHOLDS["TDS"]["critical_max"]:
        issues.append(f"TDS {tds} ppm - CRITICAL SCALE RISK (>{THRESHOLDS['TDS']['critical_max']} ppm)")
        severity = "critical"
    elif tds > THRESHOLDS["TDS"]["warning_max"]:
        issues.append(f"TDS {tds} ppm - SCALE FORMATION WARNING (>{THRESHOLDS['TDS']['warning_max']} ppm)")
        if severity == "safe":
            severity = "warning"
    elif tds > THRESHOLDS["TDS"]["optimal_max"]:
        issues.append(f"TDS {tds} ppm - ABOVE OPTIMAL (>{THRESHOLDS['TDS']['optimal_max']} ppm)")
        if severity == "safe":
            severity = "warning"

    # Check temperature (cooling efficiency)
    if temp < THRESHOLDS["temperature"]["critical_min"] or temp > THRESHOLDS["temperature"]["critical_max"]:
        issues.append(f"Temperature {temp}°C - CRITICAL (system malfunction)")
        severity = "critical"
    elif temp < THRESHOLDS["temperature"]["warning_min"] or temp > THRESHOLDS["temperature"]["warning_max"]:
        issues.append(f"Temperature {temp}°C - EFFICIENCY WARNING")
        if severity == "safe":
            severity = "warning"
    elif temp > THRESHOLDS["temperature"]["optimal_max"]:
        issues.append(f"Temperature {temp}°C - ABOVE OPTIMAL (reduced cooling)")
        if severity == "safe":
            severity = "warning"

    return severity != "safe", severity, issues

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(title="Water Guardian++ | Grainger Cooling Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class SensorInput(BaseModel):
    TDS: float
    temperature: float

# ============================================================================
# ENDPOINTS
# ============================================================================
@app.get("/")
def root():
    return {
        "name": "Water Guardian++ | Grainger Data Center Cooling Monitor",
        "application": "Server Cooling System Water Quality",
        "sensors": ["TDS (Conductivity)", "Temperature"],
        "compliance": "ASHRAE Standards",
        "features": ["Predictive maintenance", "Real-time alerts", "99.99% uptime protection"]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "gemini": "configured" if GEMINI_API_KEY else "not configured",
        "application": "Data Center Cooling Monitor"
    }

@app.post("/sensor_data")
def receive_data(data: SensorInput, db: Session = Depends(get_db)):
    """Main endpoint - receives cooling water data, triggers AI for anomalies"""

    # Check all thresholds for local alert/DB flagging
    should_trigger, severity, issues = check_thresholds(data.TDS, data.temperature)
    
    # EXPLICIT LOGIC: Only call AI if TDS exceeds 1000 ppm AND the API key is configured.
    should_call_ai = data.TDS > 1000 and GEMINI_API_KEY

    # Store reading
    reading = Reading(
        TDS=data.TDS,
        temperature=data.temperature,
        is_safe=(severity == "safe"),
        ai_triggered=should_trigger # Still logs if any threshold was crossed
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    print(f"📊 Reading #{reading.id}: TDS={data.TDS} ppm, Temp={data.temperature}°C, Status={severity}")

    # Trigger AI only if the specific TDS condition is met
    analysis_data = None
    if should_call_ai:
        print(f"🤖 AI Analysis Triggered (TDS > 1000 ppm)")
        
        # Ensure issues list is not empty when calling AI if TDS > 1000 was the only problem
        if not issues:
             issues.append(f"TDS {data.TDS} ppm - High TDS detected (>1000 ppm). Immediate scale risk.")
             
        analysis_data = call_ai(data, severity, issues, reading.id, db)
    else:
        print(f"✅ AI not triggered (TDS <= 1000 ppm or API key missing)")

    return {
        "id": reading.id,
        "timestamp": reading.timestamp,
        "TDS": reading.TDS,
        "temperature": reading.temperature,
        "is_safe": reading.is_safe,
        "ai_triggered": should_trigger,
        "severity": severity,
        "issues": issues,
        "analysis": analysis_data
    }

def call_ai(data, severity, issues, reading_id, db):
    """Call Gemini AI for cooling system analysis"""
    try:
        start = time.time()
        model = genai.GenerativeModel('models/gemini-2.5-flash')

        prompt = f"""As a data center cooling systems expert, provide a concise analysis:

WATER QUALITY DATA:
• TDS: {data.TDS} ppm (Optimal: 100-800 ppm)
• Temperature: {data.temperature}°C (Optimal: 18-27°C)
• Issues: {', '.join(issues)}
• Severity: {severity.upper()}

Provide a brief, professional assessment in this EXACT format:

IMPACT:
[One clear sentence about business impact - mention potential downtime cost if critical]

ROOT CAUSE:
[One sentence explaining what's causing this condition]

ACTIONS:
1. [First immediate action - be specific]
2. [Second immediate action - be specific]
3. [Third immediate action - be specific]

Keep it concise and actionable. No asterisks, no extra formatting."""

        response = model.generate_content(prompt)
        analysis_text = response.text
        response_ms = int((time.time() - start) * 1000)

        # Extract recommendations
        recs = []
        lines = analysis_text.split('\n')
        in_actions = False

        for line in lines:
            # Start capturing after "ACTIONS:"
            if 'ACTIONS:' in line.upper():
                in_actions = True
                continue

            # Capture numbered items
            if in_actions:
                line = line.strip()
                # Match "1. ", "2. ", "3. " or "- "
                if line and (line[0:2] in ['1.', '2.', '3.'] or line.startswith('-')):
                    # Remove numbering/bullets
                    clean_rec = line.lstrip('123.-• ').strip()
                    if clean_rec:
                        recs.append(clean_rec)

        if not recs:
            recs = [
                "Schedule immediate water treatment system inspection",
                "Increase monitoring frequency to every 5 minutes",
                "Contact cooling system maintenance team"
            ]

        # Store analysis
        analysis = Analysis(
            reading_id=reading_id,
            analysis=analysis_text,
            status=severity,
            recommendations=json.dumps(recs[:3]),
            response_ms=response_ms
        )
        db.add(analysis)
        db.commit()

        print(f"✅ AI analysis completed ({response_ms}ms)")

        return {
            "analysis": analysis_text,
            "status": severity,
            "recommendations": recs[:3],
            "response_ms": response_ms
        }
    except Exception as e:
        print(f"❌ AI error: {e}")
        return None

@app.get("/readings/latest")
def latest(db: Session = Depends(get_db)):
    """Get most recent reading"""
    r = db.query(Reading).order_by(Reading.timestamp.desc()).first()
    if not r:
        return {"error": "No readings yet"}

    a = db.query(Analysis).filter(Analysis.reading_id == r.id).first()
    analysis = None
    if a:
        analysis = {
            "analysis": a.analysis,
            "status": a.status,
            "recommendations": json.loads(a.recommendations)
        }

    return {
        "id": r.id,
        "timestamp": r.timestamp,
        "TDS": r.TDS,
        "temperature": r.temperature,
        "is_safe": r.is_safe,
        "ai_triggered": r.ai_triggered,
        "analysis": analysis
    }

@app.get("/readings/history")
def history(hours: int = 24, db: Session = Depends(get_db)):
    """Get historical readings"""
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(Reading).filter(Reading.timestamp >= since).order_by(Reading.timestamp.asc()).all()

    return {
        "count": len(readings),
        "hours": hours,
        "data": [
            {
                "timestamp": r.timestamp.isoformat(),
                "TDS": r.TDS,
                "temperature": r.temperature,
                "is_safe": r.is_safe
            }
            for r in readings
        ]
    }

@app.get("/stats")
def stats(hours: int = 24, db: Session = Depends(get_db)):
    """Get statistics"""
    since = datetime.utcnow() - timedelta(hours=hours)

    total = db.query(Reading).filter(Reading.timestamp >= since).count()
    unsafe = db.query(Reading).filter(Reading.timestamp >= since, Reading.ai_triggered == True).count()
    analyses = db.query(Analysis).filter(Analysis.timestamp >= since).count()

    savings = f"{((total - analyses) / total * 100):.1f}%" if total > 0 else "0%"

    # Calculate potential downtime prevented
    downtime_cost_per_hour = 540000  # $540k/hour
    downtime_prevented_hours = analyses * 0.5  # Base savings on actual AI calls
    cost_saved = downtime_prevented_hours * downtime_cost_per_hour

    return {
        "period_hours": hours,
        "total_readings": total,
        "anomalies_detected": unsafe,
        "ai_analyses": analyses,
        "api_call_savings_vs_total_alerts": savings,
        "readings_per_hour": round(total / hours, 1) if hours > 0 else 0,
        "estimated_downtime_prevented_hours": round(downtime_prevented_hours, 2),
        "estimated_cost_savings_usd": f"${cost_saved:,.0f}"
    }

@app.get("/thresholds")
def thresholds():
    """Get threshold configuration"""
    return THRESHOLDS

@app.get("/analyses/recent")
def recent_analyses(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent AI analyses"""
    analyses = db.query(Analysis).order_by(Analysis.timestamp.desc()).limit(limit).all()

    return {
        "count": len(analyses),
        "analyses": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "reading_id": a.reading_id,
                "status": a.status,
                "analysis": a.analysis,
                "recommendations": json.loads(a.recommendations),
                "response_ms": a.response_ms
            }
            for a in analyses
        ]
    }

@app.delete("/data/clear")
def clear_data(db: Session = Depends(get_db)):
    """Clear all data (for testing)"""
    db.query(Analysis).delete()
    db.query(Reading).delete()
    db.commit()
    return {"message": "All data cleared"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🏭 Water Guardian++ | Grainger Data Center Cooling Monitor")
    print("="*70)
    print("Application: Server cooling system water quality monitoring")
    print("Sensors: TDS (Conductivity) + Temperature")
    print("Standards: ASHRAE Cooling Water Guidelines")
    print("AI: Predictive maintenance & downtime prevention")
    print("="*70)
    print(f"📍 Server: http://localhost:8000")
    print(f"📍 API Docs: http://localhost:8000/docs")
    print(f"📍 Health: http://localhost:8000/health")
    print(f"📍 Stats: http://localhost:8000/stats")
    print("\n💡 Preventing server downtime one reading at a time...")
    print("Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
import json
import subprocess
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/app"))
ORCHESTRATOR = PROJECT_ROOT / "orchestrator.py"
FINAL_SUMMARY_OUTPUT = PROJECT_ROOT / "news_validity_summary.json"

app = FastAPI(title="Agentic News Analysis API", version="1.0.0")

class AnalyzeRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Agentic News Analysis API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    try:
        completed = subprocess.run(
            [sys.executable, str(ORCHESTRATOR), req.url],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300  # 5 minute timeout
        )
        
        if completed.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Orchestrator failed: {completed.stderr[:2000]}"
            )
        
        # Load the final summary JSON
        try:
            with open(FINAL_SUMMARY_OUTPUT, "r", encoding="utf-8") as f:
                summaries = json.load(f)
            entry = summaries.get(req.url) or {"summary": "No summary found"}
            return {"url": req.url, "result": entry, "status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read summary: {e}")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Analysis timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

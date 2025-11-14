import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import create_document, get_documents
from schemas import Waitlist

# Strict Ivy League domains only
IVY_DOMAINS = {
    "harvard.edu": "Harvard University",
    "college.harvard.edu": "Harvard University",
    "gsd.harvard.edu": "Harvard University",
    "g.harvard.edu": "Harvard University",
    "fas.harvard.edu": "Harvard University",
    "yale.edu": "Yale University",
    "princeton.edu": "Princeton University",
    "columbia.edu": "Columbia University",
    "barnard.edu": "Barnard College",
    "upenn.edu": "University of Pennsylvania",
    "wharton.upenn.edu": "University of Pennsylvania",
    "brown.edu": "Brown University",
    "dartmouth.edu": "Dartmouth College",
    "cornell.edu": "Cornell University",
}

app = FastAPI(title="Paired Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WaitlistIn(BaseModel):
    email: EmailStr
    source: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Paired API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Connected"
    except Exception as e:
        response["database"] = f"❌ {str(e)[:80]}"
    return response


def detect_ivy_school(email: str) -> Optional[str]:
    domain = email.split("@")[1].lower().strip()
    if domain in IVY_DOMAINS:
        return IVY_DOMAINS[domain]
    # handle subdomains like cs.princeton.edu
    parts = domain.split(".")
    for i in range(len(parts) - 2):
        cand = ".".join(parts[i:])
        if cand in IVY_DOMAINS:
            return IVY_DOMAINS[cand]
    for ivy_domain in IVY_DOMAINS.keys():
        if domain.endswith("." + ivy_domain):
            return IVY_DOMAINS[ivy_domain]
    return None

@app.post("/api/waitlist")
async def join_waitlist(payload: WaitlistIn):
    school = detect_ivy_school(payload.email)
    if not school:
        raise HTTPException(status_code=400, detail="Please use a valid Ivy League email to join the waitlist.")

    doc = Waitlist(email=payload.email, school=school, source=payload.source, status="pending")
    try:
        inserted_id = create_document("waitlist", doc)
        return {"ok": True, "id": inserted_id, "school": school}
    except Exception:
        raise HTTPException(status_code=500, detail="Server error. Please try again later.")

@app.get("/api/waitlist/recent")
async def recent(limit: int = 10):
    try:
        docs = get_documents("waitlist", {}, limit=limit)
        for d in docs:
            d.pop("_id", None)
        return {"ok": True, "items": docs}
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

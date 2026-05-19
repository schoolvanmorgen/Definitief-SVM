import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="School van morgen", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LEERLINGEN = {
    "5b": [
        {"id": "jan",    "naam": "Jan de Vries"},
        {"id": "lotte",  "naam": "Lotte Bakker"},
        {"id": "thomas", "naam": "Thomas Peters"},
        {"id": "sara",   "naam": "Sara Amir"},
        {"id": "noor",   "naam": "Noor Jansen"},
        {"id": "mike",   "naam": "Mike Dijkstra"},
        {"id": "fatima", "naam": "Fatima El-Amrani"},
        {"id": "lucas",  "naam": "Lucas van der Berg"},
        {"id": "emma",   "naam": "Emma Hendriks"},
        {"id": "yusuf",  "naam": "Yusuf Karahan"},
    ],
    "5a": [
        {"id": "anna", "naam": "Anna Smit"},
        {"id": "bram", "naam": "Bram de Jong"},
        {"id": "caro", "naam": "Caro Visser"},
    ],
    "6a": [
        {"id": "floor", "naam": "Floor Pietersen"},
        {"id": "gijs",  "naam": "Gijs Willems"},
        {"id": "hana",  "naam": "Hana Özdemir"},
    ],
}

CATEGORIE_REGELS = [
    (["cito","toets","score","scoort","rekenen","spelling","lezen","iep"], "Toetsresultaat"),
    (["zorg","ib","handelingsplan","opp","ondersteuning","moeite"],        "Zorgnotitie"),
    (["rapport","beoordeling","ontwikkeling","periode"],                    "Rapporttekst"),
    (["ouder","gesprek","bellen","mail","contact"],                         "Oudercontact"),
    (["afwezig","absent","ziek","verlof"],                                  "Absentie"),
    (["gedrag","sociaal","emotioneel","welbevinden"],                       "Observatie SEL"),
]

def classificeer(tekst: str) -> str:
    lager = tekst.lower()
    for woorden, cat in CATEGORIE_REGELS:
        if any(w in lager for w in woorden):
            return cat
    return "Observatie"

cache: dict = {}

class InvoerVerzoek(BaseModel):
    tekst: str
    leerling_naam: str = ""
    groep: str = ""
    systemen: list[str] = ["Parnassys"]

class BevestigVerzoek(BaseModel):
    invoer_id: str
    tekst: str
    leerling_naam: str
    categorie: str
    systemen: list[str]

@app.get("/")
async def root():
    if os.path.exists("scovamore.html"):
        return FileResponse("scovamore.html")
    return JSONResponse({"status": "School van morgen actief"})

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/groepen/{groep_id}/leerlingen")
async def get_leerlingen(groep_id: str):
    leerlingen = LEERLINGEN.get(groep_id)
    if not leerlingen:
        raise HTTPException(status_code=404, detail="Groep niet gevonden")
    return {"groep": groep_id, "leerlingen": leerlingen}

@app.post("/api/invoer/analyseer")
async def analyseer(verzoek: InvoerVerzoek):
    if not verzoek.tekst.strip():
        raise HTTPException(status_code=400, detail="Tekst leeg")
    import uuid
    invoer_id = str(uuid.uuid4())[:8]
    categorie = classificeer(verzoek.tekst)
    kort = verzoek.tekst[:65] + "…" if len(verzoek.tekst) > 65 else verzoek.tekst
    cache[invoer_id] = {"tekst": verzoek.tekst, "categorie": categorie}
    return {
        "invoer_id": invoer_id,
        "leerling_naam": verzoek.leerling_naam,
        "categorie": categorie,
        "tekst_kort": kort,
        "bestemming": f"{' + '.join(verzoek.systemen)} → Leerlingdossier → {categorie}",
    }

@app.post("/api/invoer/bevestig")
async def bevestig(verzoek: BevestigVerzoek):
    cache.pop(verzoek.invoer_id, None)
    return {
        "status": "gesynchroniseerd",
        "bericht": f"Gesynchroniseerd naar {' + '.join(verzoek.systemen)}",
        "timestamp": datetime.now().isoformat(),
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

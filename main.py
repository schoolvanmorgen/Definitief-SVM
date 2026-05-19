"""
School van morgen — main.py
Minimale FastAPI backend, klaar voor Railway deployment.
Geen externe diensten vereist om op te starten.
"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="School van morgen", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Demo data ────────────────────────────────────────────────────────────────

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
        {"id": "anna",  "naam": "Anna Smit"},
        {"id": "bram",  "naam": "Bram de Jong"},
        {"id": "caro",  "naam": "Caro Visser"},
        {"id": "daan",  "naam": "Daan Mulder"},
        {"id": "eva",   "naam": "Eva van Dijk"},
    ],
    "6a": [
        {"id": "floor", "naam": "Floor Pietersen"},
        {"id": "gijs",  "naam": "Gijs Willems"},
        {"id": "hana",  "naam": "Hana Özdemir"},
        {"id": "iris",  "naam": "Iris de Boer"},
        {"id": "joost", "naam": "Joost Bakker"},
    ],
    "3b": [
        {"id": "kees",   "naam": "Kees van Dam"},
        {"id": "laura",  "naam": "Laura Hendriks"},
        {"id": "mohamed","naam": "Mohamed Saidi"},
        {"id": "nina",   "naam": "Nina Groot"},
        {"id": "olaf",   "naam": "Olaf Vermeer"},
    ],
}

NOTITIES = [
    {
        "id": "n001",
        "leerling_naam": "Lotte Bakker",
        "initialen": "LB",
        "categorie": "Toetsresultaat",
        "tekst": "Cito rekenen scoort V — moeite met getalbegrip. Besproken met IB-er.",
        "tijdstip": "Vandaag 08:41",
    },
    {
        "id": "n002",
        "leerling_naam": "Jan de Vries",
        "initialen": "JV",
        "categorie": "Zorgnotitie",
        "tekst": "Afgeleid tijdens de les, mogelijk thuissituatie. Ouders bellen volgende week.",
        "tijdstip": "Gisteren 14:12",
    },
    {
        "id": "n003",
        "leerling_naam": "Sara Amir",
        "initialen": "SA",
        "categorie": "Rapporttekst",
        "tekst": "Goede ontwikkeling in begrijpend lezen. Zelfstandig werken verdient aandacht.",
        "tijdstip": "Ma 13 mei",
    },
]

# ── Classificatie (lokaal, zonder Mistral) ───────────────────────────────────

CATEGORIE_REGELS = [
    (["cito","toets","score","scoort","lvs","rekenen","spelling","lezen","iep","dia"], "Toetsresultaat"),
    (["zorg","ib-er","ib ","handelingsplan","opp","ondersteuning","moeite"],           "Zorgnotitie"),
    (["rapport","beoordeling","ontwikkeling","periode"],                                "Rapporttekst"),
    (["ouder","gesprek","bellen","mail","contact"],                                     "Oudercontact"),
    (["afwezig","absent","ziek","verlof","verzuim"],                                    "Absentie"),
    (["gedrag","sociaal","emotioneel","welbevinden","pesten"],                          "Observatie SEL"),
]

def classificeer(tekst: str) -> str:
    lager = tekst.lower()
    for woorden, categorie in CATEGORIE_REGELS:
        if any(w in lager for w in woorden):
            return categorie
    return "Observatie"

# ── Pydantic modellen ────────────────────────────────────────────────────────

class InvoerVerzoek(BaseModel):
    tekst: str
    leerling_id: str = ""
    leerling_naam: str = ""
    groep: str = ""
    systemen: list[str] = ["Parnassys"]

class BevestigVerzoek(BaseModel):
    invoer_id: str
    tekst: str
    leerling_naam: str
    categorie: str
    systemen: list[str]

# Tijdelijke opslag
cache: dict = {}

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    if os.path.exists("scovamore.html"):
        return FileResponse("scovamore.html")
    return JSONResponse({"status": "School van morgen API actief", "versie": "0.1.0"})

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "versie": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/api/groepen")
async def get_groepen():
    return {"groepen": list(LEERLINGEN.keys())}

@app.get("/api/groepen/{groep_id}/leerlingen")
async def get_leerlingen(groep_id: str):
    leerlingen = LEERLINGEN.get(groep_id)
    if not leerlingen:
        raise HTTPException(status_code=404, detail=f"Groep {groep_id} niet gevonden")
    return {"groep": groep_id, "leerlingen": leerlingen}

@app.get("/api/notities")
async def get_notities():
    return {"notities": NOTITIES}

@app.post("/api/invoer/analyseer")
async def analyseer(verzoek: InvoerVerzoek):
    if not verzoek.tekst.strip():
        raise HTTPException(status_code=400, detail="Tekst mag niet leeg zijn")

    import uuid
    invoer_id = str(uuid.uuid4())[:8]
    categorie = classificeer(verzoek.tekst)
    tekst_kort = verzoek.tekst[:65] + "…" if len(verzoek.tekst) > 65 else verzoek.tekst
    systemen_str = " + ".join(verzoek.systemen)

    cache[invoer_id] = {
        "tekst": verzoek.tekst,
        "categorie": categorie,
        "leerling_naam": verzoek.leerling_naam,
        "systemen": verzoek.systemen,
    }

    return {
        "invoer_id": invoer_id,
        "leerling_naam": verzoek.leerling_naam,
        "categorie": categorie,
        "tekst_kort": tekst_kort,
        "bestemming": f"{systemen_str} → Leerlingdossier → {categorie}",
    }

@app.post("/api/invoer/bevestig")
async def bevestig(verzoek: BevestigVerzoek):
    systemen_str = " + ".join(verzoek.systemen)

    # Cache opruimen
    if verzoek.invoer_id in cache:
        del cache[verzoek.invoer_id]

    return {
        "status": "gesynchroniseerd",
        "bericht": f"Gesynchroniseerd naar {systemen_str}",
        "timestamp": datetime.now().isoformat(),
    }

# ── Start ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

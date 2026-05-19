<<<<<<< HEAD
=======
"""
School van morgen — main.py
Minimale FastAPI backend, klaar voor Railway deployment.
Geen externe diensten vereist om op te starten.
"""

>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
=======
from fastapi.staticfiles import StaticFiles
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
from pydantic import BaseModel

app = FastAPI(title="School van morgen", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
=======
# ── Demo data ────────────────────────────────────────────────────────────────

>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
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
<<<<<<< HEAD
        {"id": "anna", "naam": "Anna Smit"},
        {"id": "bram", "naam": "Bram de Jong"},
        {"id": "caro", "naam": "Caro Visser"},
=======
        {"id": "anna",  "naam": "Anna Smit"},
        {"id": "bram",  "naam": "Bram de Jong"},
        {"id": "caro",  "naam": "Caro Visser"},
        {"id": "daan",  "naam": "Daan Mulder"},
        {"id": "eva",   "naam": "Eva van Dijk"},
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
    ],
    "6a": [
        {"id": "floor", "naam": "Floor Pietersen"},
        {"id": "gijs",  "naam": "Gijs Willems"},
        {"id": "hana",  "naam": "Hana Özdemir"},
<<<<<<< HEAD
    ],
}

CATEGORIE_REGELS = [
    (["cito","toets","score","scoort","rekenen","spelling","lezen","iep"], "Toetsresultaat"),
    (["zorg","ib","handelingsplan","opp","ondersteuning","moeite"],        "Zorgnotitie"),
    (["rapport","beoordeling","ontwikkeling","periode"],                    "Rapporttekst"),
    (["ouder","gesprek","bellen","mail","contact"],                         "Oudercontact"),
    (["afwezig","absent","ziek","verlof"],                                  "Absentie"),
    (["gedrag","sociaal","emotioneel","welbevinden"],                       "Observatie SEL"),
=======
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
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
]

def classificeer(tekst: str) -> str:
    lager = tekst.lower()
<<<<<<< HEAD
    for woorden, cat in CATEGORIE_REGELS:
        if any(w in lager for w in woorden):
            return cat
    return "Observatie"

cache: dict = {}

class InvoerVerzoek(BaseModel):
    tekst: str
=======
    for woorden, categorie in CATEGORIE_REGELS:
        if any(w in lager for w in woorden):
            return categorie
    return "Observatie"

# ── Pydantic modellen ────────────────────────────────────────────────────────

class InvoerVerzoek(BaseModel):
    tekst: str
    leerling_id: str = ""
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
    leerling_naam: str = ""
    groep: str = ""
    systemen: list[str] = ["Parnassys"]

class BevestigVerzoek(BaseModel):
    invoer_id: str
    tekst: str
    leerling_naam: str
    categorie: str
    systemen: list[str]

<<<<<<< HEAD
=======
# Tijdelijke opslag
cache: dict = {}

# ── Routes ───────────────────────────────────────────────────────────────────

>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
@app.get("/")
async def root():
    if os.path.exists("scovamore.html"):
        return FileResponse("scovamore.html")
<<<<<<< HEAD
    return JSONResponse({"status": "School van morgen actief"})

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
=======
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
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459

@app.get("/api/groepen/{groep_id}/leerlingen")
async def get_leerlingen(groep_id: str):
    leerlingen = LEERLINGEN.get(groep_id)
    if not leerlingen:
<<<<<<< HEAD
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
=======
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

>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
    return {
        "invoer_id": invoer_id,
        "leerling_naam": verzoek.leerling_naam,
        "categorie": categorie,
<<<<<<< HEAD
        "tekst_kort": kort,
        "bestemming": f"{' + '.join(verzoek.systemen)} → Leerlingdossier → {categorie}",
=======
        "tekst_kort": tekst_kort,
        "bestemming": f"{systemen_str} → Leerlingdossier → {categorie}",
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459
    }

@app.post("/api/invoer/bevestig")
async def bevestig(verzoek: BevestigVerzoek):
<<<<<<< HEAD
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
=======
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
>>>>>>> 0a6341f71d22b9699af485d6fb5aa72b7ae2b459

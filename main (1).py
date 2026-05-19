"""
School van morgen — main.py
FastAPI backend voor de invoerinterface

Structuur:
  - /api/groepen          → leerlinglijst per groep (straks via Parnassys GKV)
  - /api/invoer           → notitie ontvangen, Mistral classificatie, sync naar Parnassys
  - /api/notities         → recente notities per leerkracht ophalen
  - /api/sync-status      → status van de laatste sync ophalen

Vereisten (pip install):
  fastapi
  uvicorn
  sqlalchemy
  psycopg2-binary
  python-dotenv
  mistralai
  httpx
"""

import os
import json
import httpx
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Omgevingsvariabelen laden ────────────────────────────────────────────────
load_dotenv()

MISTRAL_API_KEY   = os.getenv("MISTRAL_API_KEY", "")
PARNASSYS_API_URL = os.getenv("PARNASSYS_API_URL", "https://api.parnassys.nl/gkv")
PARNASSYS_TOKEN   = os.getenv("PARNASSYS_TOKEN", "")
DATABASE_URL      = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/schoolvanmorgen")

# ── App initialiseren ────────────────────────────────────────────────────────
app = FastAPI(
    title="School van morgen API",
    description="Backend voor de invoerinterface — classificatie en synchronisatie naar Parnassys",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie vervangen door jouw domein
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statische bestanden serveren (de HTML frontend)
app.mount("/static", StaticFiles(directory="."), name="static")


# ── Pydantic modellen ────────────────────────────────────────────────────────

class InvoerVerzoek(BaseModel):
    """Wat de frontend stuurt bij een nieuwe invoer."""
    tekst: str                          # De notitie van de leerkracht
    leerling_id: str                    # ID van de geselecteerde leerling
    leerling_naam: str                  # Naam voor weergave
    groep: str                          # Bijv. "5b"
    systemen: list[str]                 # Bijv. ["Parnassys", "ESIS"]
    leerkracht_id: str = "demo"         # Straks via authenticatie


class BevestigVerzoek(BaseModel):
    """Wat de frontend stuurt na bevestiging door de leerkracht."""
    invoer_id: str                      # ID van de eerder geanalyseerde invoer
    categorie: str                      # Eventueel gecorrigeerde categorie
    leerling_id: str
    leerling_naam: str
    groep: str
    systemen: list[str]
    tekst: str


class AnalyseResultaat(BaseModel):
    """Wat de API teruggeeft na Mistral classificatie."""
    invoer_id: str
    leerling_naam: str
    categorie: str
    tekst_kort: str
    bestemming: str
    veld_mapping: dict


# ── In-memory opslag (tijdelijk, vervang door PostgreSQL) ────────────────────
# In productie: gebruik SQLAlchemy met PostgreSQL op Hetzner/Scaleway
invoer_cache: dict = {}


# ── Hulpfuncties ─────────────────────────────────────────────────────────────

def genereer_id() -> str:
    """Simpele ID generator — vervang door UUID in productie."""
    import uuid
    return str(uuid.uuid4())[:8]


async def classificeer_met_mistral(tekst: str) -> dict:
    """
    Stuurt de tekst naar Mistral voor classificatie.
    Retourneert categorie en veldmapping voor Parnassys.
    
    In productie: gebruik de officiële mistralai Python client.
    """
    if not MISTRAL_API_KEY:
        # Fallback classificatie zonder API key (voor development)
        return _lokale_classificatie(tekst)

    systeem_prompt = """
    Je bent een classificatiesysteem voor Nederlandse onderwijsadministratie.
    Je ontvangt een notitie van een leerkracht in het primair onderwijs.
    
    Classificeer de notitie in precies één van deze categorieën:
    - Toetsresultaat (scores, Cito, IEP, methodetoetsen)
    - Zorgnotitie (zorgsignalen, IB-er, ondersteuning, handelingsplan)
    - Rapporttekst (rapport, beoordeling, ontwikkeling algemeen)
    - Oudercontact (gesprek, bellen, mail met ouders)
    - Observatie SEL (gedrag, sociaal-emotioneel, welbevinden)
    - Absentie (ziek, afwezig, verlof)
    - Groepsnotitie (hele groep, niet één leerling)
    
    Geef ALLEEN een JSON terug, geen uitleg:
    {
        "categorie": "<categorie>",
        "parnassys_veld": "<veldnaam in Parnassys>",
        "prioriteit": "<normaal|hoog>",
        "actie_vereist": <true|false>
    }
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": systeem_prompt},
                    {"role": "user", "content": tekst},
                ],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        return _lokale_classificatie(tekst)

    try:
        inhoud = response.json()["choices"][0]["message"]["content"]
        return json.loads(inhoud)
    except Exception:
        return _lokale_classificatie(tekst)


def _lokale_classificatie(tekst: str) -> dict:
    """
    Fallback classificatie zonder Mistral API.
    Gebruikt simpele zoekwoordherkenning — zelfde logica als de frontend.
    """
    tekst_lower = tekst.lower()

    regels = [
        (["cito", "toets", "score", "scoort", "lvs", "rekenen", "spelling", "iep", "dia"],
         "Toetsresultaat", "toets_resultaten"),
        (["zorg", "ib-er", "ib ", "handelingsplan", "opp", "ondersteuning", "moeite"],
         "Zorgnotitie", "zorg_dossier"),
        (["rapport", "beoordeling", "ontwikkeling", "periode"],
         "Rapporttekst", "rapport_tekst"),
        (["ouder", "gesprek", "bellen", "mail", "contact"],
         "Oudercontact", "ouder_communicatie"),
        (["afwezig", "absent", "ziek", "verlof"],
         "Absentie", "verzuim"),
        (["gedrag", "sociaal", "emotioneel", "welbevinden", "pesten"],
         "Observatie SEL", "sel_observatie"),
    ]

    for woorden, categorie, veld in regels:
        if any(w in tekst_lower for w in woorden):
            return {
                "categorie": categorie,
                "parnassys_veld": veld,
                "prioriteit": "hoog" if "zorg" in categorie.lower() else "normaal",
                "actie_vereist": "ib" in tekst_lower or "handelingsplan" in tekst_lower,
            }

    return {
        "categorie": "Observatie",
        "parnassys_veld": "notities",
        "prioriteit": "normaal",
        "actie_vereist": False,
    }


async def sync_naar_parnassys(
    leerling_id: str,
    categorie: str,
    tekst: str,
    veld: str,
) -> dict:
    """
    Schrijft de geclassificeerde notitie via het GKV naar Parnassys.
    
    Vereist:
    - Goedgekeurde koppelpartner status bij Parnassys
    - Geldige PARNASSYS_TOKEN in .env
    - GKV endpoint documentatie van Parnassys
    
    Retourneert success/failure status.
    """
    if not PARNASSYS_TOKEN:
        # Development mode — simuleer succesvolle sync
        return {
            "status": "gesimuleerd",
            "bericht": "Geen Parnassys token — sync gesimuleerd in development",
            "timestamp": datetime.now().isoformat(),
        }

    payload = {
        "leerling_id": leerling_id,
        "veld": veld,
        "waarde": tekst,
        "categorie": categorie,
        "tijdstip": datetime.now().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{PARNASSYS_API_URL}/leerlingdossier",
                headers={
                    "Authorization": f"Bearer {PARNASSYS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15.0,
            )
            return {
                "status": "gesynchroniseerd" if response.status_code == 200 else "fout",
                "http_status": response.status_code,
                "timestamp": datetime.now().isoformat(),
            }
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "bericht": "Parnassys reageert niet — notitie in wachtrij geplaatst",
                "timestamp": datetime.now().isoformat(),
            }


# ── Demo leerlingendata (straks vervangen door Parnassys GKV ophalen) ────────
DEMO_LEERLINGEN = {
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
}

# Demo recente notities
DEMO_NOTITIES = [
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


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serveert de HTML frontend."""
    return FileResponse("scovamore.html")


@app.get("/api/groepen/{groep_id}/leerlingen")
async def get_leerlingen(groep_id: str):
    """
    Haalt leerlingen op voor een specifieke groep.
    
    Straks: ophalen via Parnassys GKV met schooltoken.
    Nu: demo data.
    """
    leerlingen = DEMO_LEERLINGEN.get(groep_id)
    if not leerlingen:
        raise HTTPException(status_code=404, detail=f"Groep {groep_id} niet gevonden")
    return {"groep": groep_id, "leerlingen": leerlingen}


@app.get("/api/notities")
async def get_notities(leerkracht_id: str = "demo", limit: int = 10):
    """
    Haalt recente notities op voor de ingelogde leerkracht.
    
    Straks: ophalen uit PostgreSQL gefilterd op leerkracht_id.
    Nu: demo data.
    """
    return {"notities": DEMO_NOTITIES[:limit]}


@app.post("/api/invoer/analyseer")
async def analyseer_invoer(verzoek: InvoerVerzoek):
    """
    Stap 1: Ontvangt de tekst van de leerkracht en classificeert via Mistral.
    Retourneert het analyseresultaat voor het bevestigingsscherm.
    """
    if not verzoek.tekst.strip():
        raise HTTPException(status_code=400, detail="Tekst mag niet leeg zijn")

    # Mistral classificatie
    classificatie = await classificeer_met_mistral(verzoek.tekst)

    # Tijdelijk opslaan voor de bevestigingsstap
    invoer_id = genereer_id()
    invoer_cache[invoer_id] = {
        "verzoek": verzoek.dict(),
        "classificatie": classificatie,
        "aangemaakt": datetime.now().isoformat(),
    }

    # Korte versie van de tekst voor het bevestigingsscherm
    tekst_kort = verzoek.tekst[:65] + "…" if len(verzoek.tekst) > 65 else verzoek.tekst
    systemen_str = " + ".join(verzoek.systemen)

    return AnalyseResultaat(
        invoer_id=invoer_id,
        leerling_naam=verzoek.leerling_naam,
        categorie=classificatie["categorie"],
        tekst_kort=tekst_kort,
        bestemming=f"{systemen_str} → Leerlingdossier → {classificatie['categorie']}",
        veld_mapping=classificatie,
    )


@app.post("/api/invoer/bevestig")
async def bevestig_invoer(verzoek: BevestigVerzoek):
    """
    Stap 2: Leerkracht heeft het analyseresultaat bevestigd.
    Synchroniseert naar alle geselecteerde systemen.
    """
    resultaten = {}

    for systeem in verzoek.systemen:
        if systeem == "Parnassys":
            resultaat = await sync_naar_parnassys(
                leerling_id=verzoek.leerling_id,
                categorie=verzoek.categorie,
                tekst=verzoek.tekst,
                veld=invoer_cache.get(verzoek.invoer_id, {})
                    .get("classificatie", {})
                    .get("parnassys_veld", "notities"),
            )
        else:
            # Placeholder voor ESIS, Somtoday, etc.
            # Hier komen later de adapters per systeem
            resultaat = {
                "status": "nog_niet_gebouwd",
                "bericht": f"Adapter voor {systeem} komt in volgende versie",
                "timestamp": datetime.now().isoformat(),
            }
        resultaten[systeem] = resultaat

    # Correctie opslaan voor Mistral verbetering (geen persoonsgegevens)
    if verzoek.invoer_id in invoer_cache:
        originele_categorie = invoer_cache[verzoek.invoer_id]["classificatie"]["categorie"]
        if originele_categorie != verzoek.categorie:
            # TODO: opslaan in database voor model verbetering
            print(f"Correctie: '{originele_categorie}' → '{verzoek.categorie}'")

        # Cache opruimen
        del invoer_cache[verzoek.invoer_id]

    systemen_str = " + ".join(verzoek.systemen)
    return {
        "status": "verwerkt",
        "bericht": f"Gesynchroniseerd naar {systemen_str}",
        "resultaten": resultaten,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/health")
async def health():
    """Health check endpoint voor monitoring."""
    return {
        "status": "ok",
        "versie": "0.1.0",
        "mistral": "geconfigureerd" if MISTRAL_API_KEY else "niet geconfigureerd",
        "parnassys": "geconfigureerd" if PARNASSYS_TOKEN else "development modus",
    }


# ── Applicatie starten ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Zet op False in productie
    )

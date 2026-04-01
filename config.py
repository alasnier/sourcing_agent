# config.py
import os
import re
import sys

# --- PARAMETRES DYNAMIQUES (CLI) ---
# Si n8n (ou le terminal) passe un argument, on le prend. Sinon, on garde 78 pour tes tests locaux.
if len(sys.argv) > 1 and not sys.argv[1].endswith(".py"):
    DEPARTEMENT = sys.argv[1].strip()
else:
    DEPARTEMENT = "78"

# --- VALIDATION STRICTE (FAIL-FAST) ---
if DEPARTEMENT is not None:
    if not re.match(r"^[0-9A-Z]{2,3}$", str(DEPARTEMENT).upper()):
        print(f"❌ ERREUR CRITIQUE : Le département '{DEPARTEMENT}' est invalide.")
        sys.exit(1)

# --- CONFIGURATION GOOGLE ---
GOOGLE_FOLDER_ID = "1OcirWyaXf0rOeDuqZWYpvxRWW964i_ux"
GOOGLE_SA_JSON = "./credentials.json"  # Le fichier téléchargé depuis GCP

METROPOLE_ONLY = True
TEMP_DIR = "./temp_data"
OUTPUT_DIR = "./results"
QPV_CODELIB_CSV = "./ref/qpv_codelib_2024.csv"

# Slugs API Data.gouv
SLUG_SIRENE = "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"
SLUG_GEOLOC = "geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques"

# --- MAPPING FICHIERS LOCAUX ---
FILES = {
    "ul": {
        "slug": SLUG_SIRENE,
        "rid": "350182c9-148a-46e0-8389-76c2ec1374a3",
        "local": "StockUniteLegale_utf8.parquet",
    },
    "etab": {
        "slug": SLUG_SIRENE,
        "rid": "a29c1297-1f92-4e2a-8f6b-8c902ce96c5f",
        "local": "StockEtablissement_utf8.parquet",
    },
    "geoloc": {
        "slug": SLUG_GEOLOC,
        "rid": "672007af-0146-491f-835c-8314d63fa44e",
        "local": "GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet",
    },
}

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("./ref", exist_ok=True)

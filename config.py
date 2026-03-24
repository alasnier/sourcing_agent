# config.py
import os
import re
import sys

# --- PARAMETRES ---
DEPARTEMENT = "78"  # ex. "78", "2A", "974"; None = pas de filtre CP

# --- VALIDATION STRICTE (FAIL-FAST) ---
if DEPARTEMENT is not None:
    # Accepte 2 à 3 caractères alphanumériques (gère Corse et DOM)
    if not re.match(r"^[0-9A-Z]{2,3}$", str(DEPARTEMENT).upper()):
        print(f"❌ ERREUR CRITIQUE : Le département '{DEPARTEMENT}' est invalide.")
        print("💡 Solution : Utilisez un format officiel (ex: '78', '01', '2A', '974').")
        sys.exit(1)

METROPOLE_ONLY = True  # Filtrer la géoloc sur EPSG=2154 (RGF93 / Lambert-93)
TEMP_DIR = "./temp_data"
OUTPUT_DIR = "./results"
QPV_CODELIB_CSV = "./ref/qpv_codelib_2024.csv"

# Slugs API Data.gouv (informatifs)
SLUG_SIRENE = "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"
SLUG_GEOLOC = "geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques"

# --- MAPPING FICHIERS LOCAUX (via RID stables) ---
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

# Création automatique des dossiers
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("./ref", exist_ok=True)
# config.py
import os

# --- PARAMETRES ---
DEPARTEMENT = "78"  # ex. "78"; None = pas de filtre CP
METROPOLE_ONLY = True  # Filtrer la géoloc sur EPSG=2154 (RGF93 / Lambert-93)
TEMP_DIR = "./temp_data"
OUTPUT_DIR = "./results"
QPV_CODELIB_CSV = (
    "./ref/qpv_codelib_2024.csv"  # mapping code→libellé utilisé au runtime
)

# Slugs API Data.gouv (informatifs)
SLUG_SIRENE = "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"
SLUG_GEOLOC = "geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques"

# --- MAPPING FICHIERS LOCAUX (via RID stables) ---
FILES = {
    "ul": {
        "slug": SLUG_SIRENE,
        "rid": "350182c9-148a-46e0-8389-76c2ec1374a3",  # StockUniteLegale_utf8.parquet
        "local": "StockUniteLegale_utf8.parquet",
    },
    "etab": {
        "slug": SLUG_SIRENE,
        "rid": "a29c1297-1f92-4e2a-8f6b-8c902ce96c5f",  # StockEtablissement_utf8.parquet
        "local": "StockEtablissement_utf8.parquet",
    },
    "geoloc": {
        "slug": SLUG_GEOLOC,
        "rid": "672007af-0146-491f-835c-8314d63fa44e",  # GeolocalisationEtablissement..._utf8.parquet
        "local": "GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet",
    },
}

# Création automatique des dossiers
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("./ref", exist_ok=True)

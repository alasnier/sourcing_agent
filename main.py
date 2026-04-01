# main.py
import os
import sys
from datetime import datetime

import gspread
import polars as pl
from google.oauth2.service_account import Credentials

import config
import downloader
import processor


def cleanup_temp():
    for f in os.listdir(config.TEMP_DIR):
        if f.endswith((".csv", ".zip", ".parquet")):
            os.remove(os.path.join(config.TEMP_DIR, f))


def drop_if_exists_pl(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    to_drop = [c for c in cols if c in df.columns]
    return df.drop(to_drop) if to_drop else df


def reorder_safely_pl(df: pl.DataFrame, desired: list[str]) -> pl.DataFrame:
    cols = df.columns
    keep = [c for c in desired if c in cols]
    tail = [c for c in cols if c not in keep]
    order = keep + tail
    return df.select([pl.col(c) for c in order])


def upload_to_gsheets(csv_path: str, sheet_name: str) -> str:
    """Upload massif du CSV vers Google Sheets et retourne le lien de partage."""
    if not os.path.exists(config.GOOGLE_SA_JSON):
        print(f"❌ ERREUR : Le fichier {config.GOOGLE_SA_JSON} est introuvable.")
        sys.exit(1)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(config.GOOGLE_SA_JSON, scopes=scopes)
    client = gspread.authorize(creds)

    # 1. Création du fichier dans ton dossier spécifique
    spreadsheet = client.create(sheet_name, folder_id=config.GOOGLE_FOLDER_ID)

    # 2. Lecture et import du CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()

    client.import_csv(spreadsheet.id, csv_content.encode("utf-8"))

    # 3. Ouverture des droits en lecture pour que le client puisse l'ouvrir sans compte
    spreadsheet.share("", role="reader", type="anyone")

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"


def main():
    start = datetime.now()

    paths = downloader.run_download()
    df = processor.process_data(paths)

    cols_to_drop = [
        "x",
        "y",
        "x_longitude",
        "y_latitude",
        "epsg",
        "plg_qp24",
        "qualite_qp24",
        "qualite_xy",
        "distance_precision",
        "plg_code_commune",
        "x_l93",
        "y_l93",
        "longitude",
        "latitude",
        "EPSG",
        "PLG_QP24",
        "QUALITE_QP24",
        "QUALITE_XY",
        "DISTANCE_PRECISION",
        "PLG_CODE_COMMUNE",
        "coordonnees_gps",
        "geocodage_distance_max_m",
        "is_qpv_poly",
        "nom_qpv_poly",
    ]
    df = drop_if_exists_pl(df, cols_to_drop)

    desired_order = [
        "siren",
        "siret",
        "type_etablissement",
        "raison_sociale",
        "code_postal",
        "ville",
        "adresse",
        "dateCreationEtablissement",
        "etatAdministratifEtablissement",
        "age_entreprise",
        "is_qpv",
        "qpv_code",
        "nom_qpv",
        "qpv_qualite",
        "geocodage_qualite",
    ]
    df = reorder_safely_pl(df, desired_order)

    # --- Exports ---
    timestamp = start.strftime("%Y%m%d_%H%M")
    dpt = config.DEPARTEMENT

    # Nommage strict demandé
    sheet_name = f"agent_qpv_n8n_python_{dpt}_{timestamp}"

    # On utilise la virgule (",") temporairement car l'import_csv Google le digère mieux par défaut
    out_csv = os.path.join(config.OUTPUT_DIR, f"{sheet_name}.csv")
    df.write_csv(out_csv, separator=",")

    # Pousse vers Drive et récupère le lien
    url_gsheet = upload_to_gsheets(out_csv, sheet_name)

    cleanup_temp()

    # --- OUTPUT POUR N8N ---
    # On imprime l'URL en toute dernière ligne pour que n8n la lise facilement.
    print(url_gsheet)


if __name__ == "__main__":
    main()

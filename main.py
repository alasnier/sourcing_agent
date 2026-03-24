# main.py
import os
from datetime import datetime

import polars as pl

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


def main():
    start = datetime.now()

    paths = downloader.run_download()
    df = processor.process_data(paths)

    # Colonnes à supprimer (doublons/superflues)
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

    # Ordre final allégé
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

    # --- Exports (Polars) ---
    timestamp = start.strftime("%Y%m%d_%H%M")
    dpt = config.DEPARTEMENT or "FRANCE"
    base_name = f"sourcing_{dpt}_{timestamp}"

    out_csv = os.path.join(config.OUTPUT_DIR, f"{base_name}.csv")
    out_parquet = os.path.join(config.OUTPUT_DIR, f"{base_name}.parquet")

    print(f"\n-> Export CSV : {out_csv}")
    df.write_csv(out_csv, separator=";", include_bom=True)

    print(f"-> Export Parquet : {out_parquet}")
    df.write_parquet(out_parquet, compression="snappy")

    cleanup_temp()
    print(f"\n--- TERMINÉ en {datetime.now() - start} ---")


if __name__ == "__main__":
    main()

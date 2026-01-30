from datetime import date
from pathlib import Path

import polars as pl

import config


def process_data(_paths) -> pl.DataFrame:
    print("\n--- ETAPE 2 : TRAITEMENT POLARS ---")

    # --- Chemins PARQUET téléchargés ---
    etab_parquet = Path(config.TEMP_DIR, "StockEtablissement_utf8.parquet")
    ul_parquet = Path(config.TEMP_DIR, "StockUniteLegale_utf8.parquet")
    geoloc_parquet = Path(
        config.TEMP_DIR,
        "GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet",
    )

    # --- UNITES LEGALES ---
    print("-> Chargement Unités Légales (Parquet)...")
    ul_lazy = (
        pl.scan_parquet(ul_parquet)
        .select(
            [
                pl.col("siren").cast(pl.Utf8),
                pl.coalesce(
                    [
                        pl.col("denominationUniteLegale"),
                        pl.col("nomUniteLegale")
                        + pl.lit(" ")
                        + pl.col("prenomUsuelUniteLegale"),
                    ]
                ).alias("raison_sociale"),
            ]
        )
        .unique(subset=["siren"])
    )

    # --- ETABLISSEMENTS ---
    print("-> Chargement Etablissements (Parquet)...")
    etab_lazy = pl.scan_parquet(etab_parquet)
    if config.DEPARTEMENT:
        print(f"   Filtre Département : {config.DEPARTEMENT}")
        etab_lazy = etab_lazy.filter(
            pl.col("codePostalEtablissement")
            .cast(pl.Utf8)
            .str.starts_with(config.DEPARTEMENT)
        )

    etab_prep = (
        etab_lazy.select(
            [
                pl.col("siren").cast(pl.Utf8),
                pl.col("siret").cast(pl.Utf8),
                pl.when(pl.col("etablissementSiege"))
                .then(pl.lit("Siège"))
                .otherwise(pl.lit("Établissement"))
                .alias("type_etablissement"),
                pl.col("codePostalEtablissement").cast(pl.Utf8).alias("code_postal"),
                pl.col("libelleCommuneEtablissement").cast(pl.Utf8).alias("ville"),
                (
                    pl.col("numeroVoieEtablissement").cast(pl.Utf8).fill_null("")
                    + pl.lit(" ")
                    + pl.col("libelleVoieEtablissement").cast(pl.Utf8).fill_null("")
                )
                .str.strip_chars()
                .alias("adresse"),
                pl.col("dateCreationEtablissement")
                .cast(pl.Utf8)
                .alias("date_creation_str"),
                pl.col("dateDebut").cast(pl.Utf8).alias("date_debut_str"),
                pl.col("etatAdministratifEtablissement")
                .cast(pl.Utf8)
                .alias("etatAdministratifEtablissement"),
            ]
        )
        .with_columns(
            [
                pl.col("date_creation_str")
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias("dateCreationEtablissement"),
                pl.col("date_debut_str")
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias("dateDebut"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("etatAdministratifEtablissement") == "F")
                .then(pl.col("dateDebut"))
                .otherwise(pl.lit(None, dtype=pl.Date))
                .alias("dateFermetureEtablissement")
            ]
        )
        .drop(["date_creation_str", "date_debut_str"])
    )

    # --- GEOLOCALISATION (Option A) ---
    print("-> Chargement Géolocalisation SIRENE (Parquet)...")
    scan_geo = pl.scan_parquet(geoloc_parquet)
    schema_geo = scan_geo.collect_schema()  # solution propre (pas de warning)

    def pick(*cands):
        for c in cands:
            if c in schema_geo:
                return c
        return None

    siret_col = pick("siret", "SIRET")
    epsg_col = pick("EPSG", "epsg")
    plg_qp24_col = pick("PLG_QP24", "plg_qp24")
    qual_qp24_col = pick("QUALITE_QP24", "qualite_qp24")
    qual_xy_col = pick("QUALITE_XY", "qualite_xy")
    code_commune_col = pick("PLG_CODE_COMMUNE", "plg_code_commune")

    selections = []
    if siret_col:
        selections.append(pl.col(siret_col).cast(pl.Utf8).alias("siret"))
    if epsg_col:
        selections.append(pl.col(epsg_col).cast(pl.Utf8).alias("EPSG"))
    if plg_qp24_col:
        selections.append(pl.col(plg_qp24_col).cast(pl.Utf8).alias("PLG_QP24"))
    if qual_qp24_col:
        selections.append(pl.col(qual_qp24_col).cast(pl.Utf8).alias("QUALITE_QP24"))
    if qual_xy_col:
        selections.append(pl.col(qual_xy_col).cast(pl.Utf8).alias("QUALITE_XY"))
    if code_commune_col:
        selections.append(
            pl.col(code_commune_col).cast(pl.Utf8).alias("PLG_CODE_COMMUNE")
        )

    geoloc_lazy = scan_geo.select(selections)

    # Métropole uniquement (EPSG=2154 – RGF93/L93) – doc Insee (jeu géoloc SIRENE)
    if config.METROPOLE_ONLY and epsg_col:
        geoloc_lazy = geoloc_lazy.filter(
            pl.col("EPSG") == "2154"
        )  # [5](https://mundobytes.com/en/How-to-open-CSV-files-in-Excel-with-UTF-8-encoding/)

    # Filtre géoloc par code commune INSEE si dispo (optimisation)
    geo_names = geoloc_lazy.collect_schema().names()
    if config.DEPARTEMENT and ("PLG_CODE_COMMUNE" in geo_names):
        geoloc_lazy = geoloc_lazy.filter(
            pl.col("PLG_CODE_COMMUNE").str.starts_with(config.DEPARTEMENT)
        )

    # --- JOINTURES ---
    print("-> Jointures en cours (Collect)...")
    df = (
        etab_prep.join(ul_lazy, on="siren", how="left")
        .join(geoloc_lazy, on="siret", how="left")
        .collect()
    )

    # --- QPV & qualités (mapping lisible) ---
    if "PLG_QP24" in df.columns:
        df = df.with_columns(
            [
                (
                    (pl.col("PLG_QP24").is_not_null())
                    & (pl.col("PLG_QP24") != "")
                    & (pl.col("PLG_QP24") != "CSZ")
                    & (pl.col("PLG_QP24") != "HZ")
                ).alias("is_qpv"),
                pl.col("PLG_QP24").alias("qpv_code"),
                pl.when(pl.col("QUALITE_QP24") == "1")
                .then(pl.lit("Sûr"))
                .when(pl.col("QUALITE_QP24") == "2")
                .then(pl.lit("Probable"))
                .when(pl.col("QUALITE_QP24") == "3")
                .then(pl.lit("Aléatoire ou indéterminé"))
                .otherwise(pl.lit(None))
                .alias("qpv_qualite"),
                pl.when(pl.col("QUALITE_XY") == "11")
                .then(pl.lit("Voie sûre, numéro trouvé"))
                .when(pl.col("QUALITE_XY") == "12")
                .then(pl.lit("Voie sûre, position aléatoire dans la voie"))
                .when(pl.col("QUALITE_XY") == "21")
                .then(pl.lit("Voie probable, numéro trouvé"))
                .when(pl.col("QUALITE_XY") == "22")
                .then(pl.lit("Voie probable, position aléatoire dans la voie"))
                .when(pl.col("QUALITE_XY") == "33")
                .then(pl.lit("Voie inconnue, position aléatoire dans la commune"))
                .otherwise(pl.lit(None))
                .alias("geocodage_qualite"),
            ]
        )
    else:
        df = df.with_columns(
            [pl.lit(None).alias("is_qpv"), pl.lit(None).alias("qpv_code")]
        )

    # --- JOINTURE SUR LE CSV de référence code→libellé (sans polygones)
    # Si le CSV n'existe pas, fallback: nom_qpv = qpv_code
    try:
        map_df = pl.read_csv(
            config.QPV_CODELIB_CSV,
            has_header=True,
            infer_schema_length=0,
        )

        # Détection souple des noms de colonnes dans le CSV (selon la source)
        def pick_csv(cols, *cands):
            lowers = {c.lower(): c for c in cols}
            for c in cands:
                if c.lower() in lowers:
                    return lowers[c.lower()]
            return None

        code_col = pick_csv(
            map_df.columns,
            "code_qp",
            "CODE_QP",
            "qp",
            "QP",
            "cod_var",
            "COD_VAR",
            "codeQPV",
            "code_qpv",
        )
        lib_col = pick_csv(
            map_df.columns,
            "lib_qp",
            "LIB_QP",
            "libQPV",
            "lib_qpv",
            "lib_var",
            "LIB_VAR",
        )

        if code_col is None or lib_col is None:
            # Impossible de détecter les colonnes: fallback propre
            df = df.with_columns(
                pl.when(pl.col("qpv_code").is_not_null())
                .then(pl.col("qpv_code"))
                .otherwise(None)
                .alias("nom_qpv")
            )
        else:
            # Normalisation du mapping -> colonnes standard : qpv_code / nom_qpv
            map_df_std = map_df.select(
                [
                    pl.col(code_col).cast(pl.Utf8).alias("qpv_code"),
                    pl.col(lib_col).cast(pl.Utf8).alias("nom_qpv"),
                ]
            ).unique(subset=["qpv_code"])

            # Jointure sur la même clé (pas de drop nécessaire)
            df = df.join(map_df_std, on="qpv_code", how="left").with_columns(
                pl.coalesce([pl.col("nom_qpv"), pl.col("qpv_code")]).alias("nom_qpv")
            )

    except FileNotFoundError:
        df = df.with_columns(
            pl.when(pl.col("qpv_code").is_not_null())
            .then(pl.col("qpv_code"))
            .otherwise(None)
            .alias("nom_qpv")
        )
    # --- AGE ENTREPRISE (logique correcte)
    today = date.today()
    df = (
        df.with_columns(
            pl.when(pl.col("dateFermetureEtablissement").is_not_null())
            .then(pl.col("dateFermetureEtablissement"))
            .otherwise(pl.lit(today).cast(pl.Date))
            .alias("_age_ref")
        )
        .with_columns(
            (
                (
                    pl.col("_age_ref") - pl.col("dateCreationEtablissement")
                ).dt.total_days()
                / 365.25
            )
            .round(1)
            .alias("age_entreprise")
        )
        .drop(["_age_ref"])
    )

    return df

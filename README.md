# 🏗️ **Sourcing Agent — README**

## 1. 🎯 Objectif du projet

Ce projet a pour but de produire un **fichier de sourcing qualifié** regroupant, pour un périmètre géographique donné (ex. département **78**), l’ensemble des **établissements** et **unités légales** issus de SIRENE, enrichis par :

*   leur **géolocalisation officielle** Insee,
*   leur **statut QPV 2024** (Quartier Prioritaire de la Politique de la Ville),
*   le **libellé officiel** du quartier (via un mapping code→nom),
*   des indicateurs métier (ex. **âge de l’entreprise**, état administratif, etc.).

Le pipeline est conçu pour être :

*   **Robuste** (sources officielles Insee / ANCT, jointures sûres, typage strict),
*   **Lean** (Polars only, aucune étape inutile, zéro géocodage),
*   **Reproductible** (téléchargements par RID stables, étapes bien découpées),
*   **100% compatible Excel** via un CSV UTF‑8 avec BOM.

***

## 2. 📚 Sources officielles utilisées

### **A. SIRENE — Unités Légales (UL)**

*   **StockUniteLegale\_utf8.parquet**
*   Source Data.gouv (RID stable)  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret)

***

### **B. SIRENE — Établissements (ETAB)**

*   **StockEtablissement\_utf8.parquet**
*   Source Data.gouv (RID stable)  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret)

***

### **C. SIRENE — Géolocalisation des Établissements (GEOLOC)**

*   **GeolocalisationEtablissement\_Sirene\_pour\_etudes\_statistiques\_utf8.parquet**
*   Contient :
    *   coordonnées X/Y Lambert‑93 (EPSG 2154),
    *   lat/lon GPS,
    *   **PLG\_QP24** (code QPV),
    *   **QUALITE\_QP24**, **QUALITE\_XY**,
    *   code commune (`PLG_CODE_COMMUNE`).
*   Publication mensuelle.  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques) [\[sig.ville.gouv.fr\]](https://sig.ville.gouv.fr/atlas/QP_2024)

***

### **D. Référentiel QPV 2024 — GeoJSON (pour extraire le libellé QPV)**

Ce fichier contient les périmètres QPV 2024 et les attributs **code\_qp** / **lib\_qp**, permettant de générer un mapping code→libellé.

👉 Disponible depuis la cartothèque / atlas ANCT :  
[Atlas des QPV 2024](https://sig.ville.gouv.fr/atlas/QP_2024) [\[doc.data.gouv.fr\]](https://doc.data.gouv.fr/api/reference/)

👉 Ou via data.gouv (exemple GeoJSON complet utilisé par la communauté)  
<https://static.data.gouv.fr/resources/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20250206-161839/qp2024-france-hexagonale-outre-mer-wgs84-epsg4326.geojson> (structure montrée ici) [\[data-inter...e.ademe.fr\]](https://data-interne.ademe.fr/applications/cartes-geojson)

Ce fichier permet de produire le mapping :

    ./ref/qpv_codelib_2024.csv

***

## 3. 📦 Résultats générés

Chaque exécution produit deux fichiers dans `./results/` :

### ✔️ CSV : `sourcing_<DEPARTEMENT>_<TIMESTAMP>.csv`

*   encodage **UTF‑8 avec BOM** pour affichage correct dans Excel
*   séparateur `;`

### ✔️ Parquet : `sourcing_<DEPARTEMENT>_<TIMESTAMP>.parquet`

*   compression **snappy**
*   préservé pour les usages data / analytics.

***

## 📑 **Colonnes de sortie : description & origine**

Voici la table finale générée par le pipeline, avec l’origine **UL / ETAB / GEOLOC / Calcul** :

| Colonne                          | Description                                                    | Source  |
| -------------------------------- | -------------------------------------------------------------- | ------- |
| `siren`                          | identifiant personne morale                                    | UL      |
| `siret`                          | identifiant établissement                                      | ETAB    |
| `type_etablissement`             | “Siège” ou “Établissement”                                     | ETAB    |
| `raison_sociale`                 | nom complet UL (dénomination ou nom+prénom)                    | UL      |
| `code_postal`                    | code postal                                                    | ETAB    |
| `ville`                          | libellé commune                                                | ETAB    |
| `adresse`                        | numéro + voie                                                  | ETAB    |
| `dateCreationEtablissement`      | date de création                                               | ETAB    |
| `etatAdministratifEtablissement` | A (actif) ou F (fermé)                                         | ETAB    |
| `dateFermetureEtablissement`     | date officielle de fermeture (si F)                            | ETAB    |
| `age_entreprise`                 | âge **calculé** (= fermeture–création ou aujourd’hui–création) | CALCUL  |
| `is_qpv`                         | booléen : établissement en QPV (oui/non), issu de PLG\_QP24    | GEOLOC  |
| `qpv_code`                       | code QPV 2024 (format QNXXXYYZ)                                | GEOLOC  |
| `nom_qpv`                        | **libellé officiel**, via CSV code→libellé                     | MAPPING |
| `qpv_qualite`                    | qualité QPV (1= Sûr, 2= Probable, 3= Aléatoire/indéterminé)    | GEOLOC  |
| `geocodage_qualite`              | libellé qualité du géocodage adresse (11/12/21/22/33)          | GEOLOC  |

**Colonnes explicitement supprimées** juste avant export :

*   toutes coordonnées (X, Y, lat, lon),
*   EPSG, PLG\_CODE\_COMMUNE, QUALITE\_\*,
*   colonnes techniques `_age_ref`, `dateDebut`, etc.,
*   données audit (is\_qpv\_poly) non utilisées.

***

## 🔧 Fonctionnement du pipeline (résumé technique)

1.  **Téléchargement automatique** via RID (UL, ETAB, GEOLOC)
2.  Chargement Polars (100 % lazy → collect)
3.  Préparation UL & ETAB (structures propres + typage strict)
4.  Préparation GEOLOC (EPSG 2154, QPV24, qualité)
5.  Jointures (UL ← ETAB ← GEOLOC)
6.  Enrichissement QPV (is\_qpv, qpv\_code, qualités)
7.  **Join sur mapping code→libellé** (sans géométrie)
8.  Calcul âge entreprise
9.  Nettoyage & réordonnancement des colonnes
10. Export CSV (UTF‑8 BOM) + Parquet

# 🏗️ **Sourcing Agent — README**

## 1. 🎯 Objectif du projet

Ce projet a pour but de produire un **fichier de sourcing qualifié** regroupant, pour un périmètre géographique donné (ex. département **78**), l’ensemble des **établissements en exercice (actifs)** et **unités légales** issus de SIRENE, enrichis par :

* leur **géolocalisation officielle** Insee,
* leur **statut QPV 2024** (Quartier Prioritaire de la Politique de la Ville),
* le **libellé officiel** du quartier (via un mapping code→nom),
* des indicateurs métier (ex. **âge de l’entreprise**, etc.).

Le pipeline est conçu pour être :

* **Robuste** (Fail-Fast sur les inputs, sources officielles Insee / ANCT, typage strict),
* **Lean** (Polars only, pushdown predicates pour ne charger que les entreprises actives, zéro géocodage),
* **Reproductible** (téléchargements par RID stables, étapes bien découpées),
* **100% compatible Excel** via un CSV UTF‑8 avec BOM.

---

## 2. 📚 Sources officielles utilisées

### **A. SIRENE — Unités Légales (UL)**
* **StockUniteLegale_utf8.parquet**
* Source Data.gouv (RID stable)  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret)

### **B. SIRENE — Établissements (ETAB)**
* **StockEtablissement_utf8.parquet**
* Source Data.gouv (RID stable)  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret)

### **C. SIRENE — Géolocalisation des Établissements (GEOLOC)**
* **GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet**
* Contient : coordonnées X/Y Lambert‑93 (EPSG 2154), **PLG_QP24** (code QPV), code commune (`PLG_CODE_COMMUNE`).
* Publication mensuelle.  
    👉 [Lien officiel du dataset](https://www.data.gouv.fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques)

### **D. Référentiel QPV 2024 — CSV de mapping**
Ce fichier permet de produire le mapping code→libellé et doit être placé ici :
`./ref/qpv_codelib_2024.csv`

---

## 3. 📦 Résultats générés

Chaque exécution produit deux fichiers dans `./results/` :

### ✔️ CSV : `sourcing_<DEPARTEMENT>_<TIMESTAMP>.csv`
* encodage **UTF‑8 avec BOM** pour affichage correct et direct dans Excel
* séparateur `;`

### ✔️ Parquet : `sourcing_<DEPARTEMENT>_<TIMESTAMP>.parquet`
* compression **snappy**
* préservé pour les usages data / analytics aval.

---

## 4. 📑 Colonnes de sortie : description & origine

Voici la table finale générée par le pipeline. *Note : seules les sociétés actives sont exportées.*

| Colonne | Description | Source |
| :--- | :--- | :--- |
| `siren` | identifiant personne morale | UL |
| `siret` | identifiant établissement | ETAB |
| `type_etablissement` | “Siège” ou “Établissement” | ETAB |
| `raison_sociale` | nom complet UL (dénomination ou nom+prénom) | UL |
| `code_postal` | code postal | ETAB |
| `ville` | libellé commune | ETAB |
| `adresse` | numéro + voie | ETAB |
| `dateCreationEtablissement` | date de création | ETAB |
| `etatAdministratifEtablissement` | Toujours `A` (Actif) car filtré à la source | ETAB |
| `age_entreprise` | âge calculé (Aujourd’hui – création) en années | CALCUL |
| `is_qpv` | booléen : établissement en QPV (oui/non) | GEOLOC |
| `qpv_code` | code QPV 2024 (format QNXXXYYZ) | GEOLOC |
| `nom_qpv` | libellé officiel du quartier | MAPPING |
| `qpv_qualite` | qualité QPV (Sûr, Probable, Aléatoire/indéterminé) | GEOLOC |
| `geocodage_qualite` | fiabilité de la position géographique | GEOLOC |

**Colonnes explicitement supprimées avant export :**
Toutes les coordonnées brutes (X, Y, lat, lon), dates de fermeture (devenues inutiles), données de contrôle technique, et informations redondantes.

---

## 5. 🔧 Fonctionnement du pipeline (résumé technique)

1.  **Validation (Fail-Fast)** : Vérification du format du département fourni.
2.  **Téléchargement** : Acquisition automatique via RID (UL, ETAB, GEOLOC).
3.  **Chargement Polars & Pushdown** : Filtrage immédiat pour ne conserver **que** les établissements actifs (`état = A`), réduisant massivement la consommation RAM.
4.  **Préparation GEOLOC** : Filtrage EPSG 2154 et département géographique.
5.  **Jointures** : UL ← ETAB ← GEOLOC.
6.  **Enrichissement métier** : Application des flags QPV, jointure avec le libellé officiel et calcul de l'âge de l'entreprise.
7.  **Nettoyage** : Purge des colonnes techniques.
8.  **Export** : CSV (UTF‑8 BOM) + Parquet.
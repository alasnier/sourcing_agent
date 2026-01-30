# downloader.py
import os

import requests

import config


class SireneFetcher:
    """Téléchargement robuste via RID /datasets/r/{rid}."""

    @staticmethod
    def download(url, filename):
        path = os.path.join(config.TEMP_DIR, filename)
        if os.path.exists(path):
            print(f"   OK (Déjà complet) : {filename}")
            return path

        print(f"-> Téléchargement {filename} ...")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        print(f"   Succès : {filename}")
        return path

    @staticmethod
    def download_from_rid(rid, filename):
        """Toujours la dernière version de la ressource."""
        url_stable = f"https://www.data.gouv.fr/api/1/datasets/r/{rid}"
        return SireneFetcher.download(url_stable, filename)


def run_download():
    print("--- ETAPE 1 : ACQUISITION ---")
    paths = {}
    fetcher = SireneFetcher()

    for key, info in config.FILES.items():
        print(f"-> Téléchargement par RID pour {key} ...")
        local_path = fetcher.download_from_rid(info["rid"], info["local"])
        paths[key] = {"path": local_path, "meta": {"rid": info["rid"]}}

    return paths


if __name__ == "__main__":
    run_download()

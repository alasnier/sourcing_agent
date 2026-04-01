# ⚙️ Documentation du Workflow Automatisé : n8n x Python (Sourcing Agent)

Ce document décrit l'architecture, le parcours utilisateur et l'implémentation technique de l'automatisation du Sourcing Agent via Telegram et n8n.

## 1. 🎯 Parcours Utilisateur (Vue Fonctionnelle)

L'objectif est d'offrir une expérience fluide et asynchrone à la cliente, directement depuis son téléphone, sans interface complexe.

1. **Requête :** La cliente ouvre Telegram et envoie un numéro de département au bot (ex: `"91"`).
2. **Validation instantanée (Fail-Fast) :** * *Si le format est invalide* (ex: "Essonne" ou "91a") : Le bot répond immédiatement : *"❌ Format invalide. Tapez un numéro de département (ex: 78)."* Le processus s'arrête.
   * *Si le format est valide* : Le bot répond : *"⏳ Traitement en cours pour le département 91..."*.
3. **Traitement (Invisible pour la cliente) :** Le serveur calcule l'extraction SIRENE croisée avec les données QPV.
4. **Export Google Sheets :** Les données qualifiées sont écrites directement dans un fichier Google Sheets sécurisé sur le Cloud.
5. **Livraison :** La cliente reçoit un dernier message Telegram avec le lien d'accès : *"✅ Extraction terminée. Voici le fichier : https://docs.google.com/spreadsheets/d/..."*.

---

## 2. 🏗️ Choix d'Architecture (Le "Pourquoi")

L'architecture sépare strictement l'orchestration (n8n) de la donnée (Python).

* **Protection de la RAM (Anti-OOM) :** n8n n'est pas conçu pour faire transiter de gros volumes de données en mémoire. Faire lire un CSV de 100 000 lignes à n8n pour l'envoyer vers Google Sheets ferait planter le serveur (VPS). 
* **Séparation des responsabilités :** n8n gère l'UX (Telegram) et le routage. Python gère la donnée lourde (Polars) et l'API Google Sheets.
* **Pérennité et scalabilité :** Le code vit sur l'OS du serveur (clone Git, environnement virtuel propre), pas dans un nœud n8n. Cela garantit un versioning propre et permet de changer d'orchestrateur demain sans réécrire une seule ligne de code.

---

## 3. 💻 Implémentation Technique (Configuration n8n)

Le workflow n8n se compose de 6 nœuds consécutifs.

### Nœud 1 : Telegram Trigger (Point d'entrée)
* **Action :** Déclenche le workflow à chaque nouveau message texte reçu.
* **Configuration :** * Connecter les *Credentials Telegram API*.
  * Updates : `message` (ignore les autres events comme l'ajout à un groupe).

### Nœud 2 : If (Le routeur / Fail-Fast)
* **Action :** Valide la donnée d'entrée via une expression régulière pour protéger le serveur des requêtes inutiles.
* **Configuration :**
  * Value 1 : `{{ $json.message.text }}`
  * Operation : `Regex Match`
  * Value 2 : `^[0-9A-Z]{2,3}$` *(Autorise les formats type 78, 01, 2A, 974)*

### Nœud 3 : Telegram (Branche *False* du If)
* **Action :** Rejette la demande instantanément (Fail-Fast).
* **Configuration :**
  * Chat ID : `{{ $('Telegram Trigger').item.json.message.chat.id }}`
  * Text : `❌ Format invalide. Merci d'envoyer uniquement un numéro de département valide (ex: 78, 2A, 974).`

### Nœud 4 : Telegram (Branche *True* du If - Étape 1)
* **Action :** Gère la charge mentale de la cliente en lui confirmant la prise en compte.
* **Configuration :**
  * Chat ID : `{{ $('Telegram Trigger').item.json.message.chat.id }}`
  * Text : `⏳ C'est noté ! Extraction SIRENE en cours pour le département {{ $('Telegram Trigger').item.json.message.text }}... Cela peut prendre quelques instants.`

### Nœud 5 : Execute Command (Branche *True* - Étape 2)
* **Action :** Fait le pont vers le système d'exploitation du VPS pour exécuter le pipeline Data. Attend la fin du script.
* **Configuration :**
  * Command : 
    ```bash
    cd /opt/sourcing_agent && /opt/sourcing_agent/venv/bin/python main.py {{ $('Telegram Trigger').item.json.message.text }}
    ```
  * *Note système :* Utilisation obligatoire de chemins absolus car n8n s'exécute avec son propre utilisateur système et ses propres variables d'environnement.

### Nœud 6 : Telegram (Branche *True* - Étape 3 finale)
* **Action :** Renvoie le résultat à la cliente.
* **Configuration :**
  * Chat ID : `{{ $('Telegram Trigger').item.json.message.chat.id }}`
  * Text : `✅ Extraction terminée avec succès !\n\nVoici le lien vers le fichier qualifié :\n{{ $json.stdout }}`
  * *Note :* `{{ $json.stdout }}` capture la sortie standard finale de Python (le dernier `print()` contenant l'URL du Google Sheet).

---

## 4. 🚀 Déploiement sur le Serveur (VPS)

Pour que le nœud *Execute Command* fonctionne, le code doit être déployé proprement sur le système d'exploitation (Linux/Ubuntu).

1. **Clonage du dépôt :**
   ```bash
   cd /opt
   git clone [https://github.com/alasnier/sourcing_agent.git](https://github.com/alasnier/sourcing_agent.git)
   cd sourcing_agent
Création de l'environnement virtuel isolé :

Bash
python3 -m venv venv
source venv/bin/activate
Installation des dépendances :

Bash
pip install -r requirements.txt
Authentification Google : Placer le fichier de service account .json requis par le script Python pour l'écriture Google Sheets à l'emplacement défini dans config.py.
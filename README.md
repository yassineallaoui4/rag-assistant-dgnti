# Assistant courriers DSIT

Assistant documentaire français/arabe pour consulter les courriers de la Province de Berkane. L'interface utilise Streamlit, les PDF sont extraits avec PyMuPDF et Tesseract, la recherche utilise E5 et Chroma, et les réponses sont générées via Groq.

## Installation et lancement sous Windows

Python 3.11 ou supérieur et Tesseract avec les langues `fra` et `ara` sont nécessaires. Les versions des dépendances directes correspondent à l'environnement de développement vérifié.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Créez `.env` à partir de `.env.example` si vous n'avez pas déjà ce fichier, puis renseignez `GROQ_API_KEY`. Ne remplacez pas un `.env` existant. Le chemin de Tesseract peut être défini avec `TESSERACT_CMD`.

Le modèle de réponse par défaut est `openai/gpt-oss-120b`, vérifié avec l'API Groq. Vous pouvez le changer avec `GROQ_MODEL` dans `.env`, puis relancer l'application. L'ancien `llama-3.3-70b-versatile` renvoyait `model_not_found` avec la clé du projet. Les erreurs de modèle, d'authentification, de quota, de connexion et de recherche locale sont maintenant distinguées dans l'interface.

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

Placez vos documents dans `pdfs/`, puis cliquez sur **Mettre à jour la base**. Le dossier `pdfs22/` n'est pas indexé. Les chemins documentaires sont résolus depuis le projet, indépendamment du répertoire de lancement. Le modèle d'embedding est téléchargé au premier usage. Groq reçoit la question, les derniers échanges et les extraits documentaires sélectionnés ; l'OCR et les embeddings sont calculés localement.

## Indexation et migration

```powershell
.\venv\Scripts\python.exe ingest.py
.\venv\Scripts\python.exe ingest.py --rebuild
```

La synchronisation compare le SHA-256 de chaque PDF : ajouts, modifications sous le même nom et suppressions sont détectés. Les textes des PDF inchangés sont réutilisés ; les embeddings sont recalculés pour la nouvelle génération. `--rebuild` refait aussi l'extraction et l'OCR.

Une mise à jour construit et vérifie une nouvelle collection avant de publier `chroma_db/active_index.json`. L'ancienne collection reste disponible en cas d'échec. Les anciennes générations sont conservées et occupent donc de l'espace disque. N'exécutez qu'un seul processus d'indexation à la fois. Le bouton de mise à jour efface la conversation de la session courante pour éviter d'afficher ses anciennes sources.

Une base historique sans manifeste est lue dans sa collection `langchain`, avec le modèle configuré et l'ancien encodage sans préfixes. Cela suppose qu'elle a été construite avec ce même modèle. La première mise à jour explicite la migre vers des vecteurs E5 normalisés avec préfixes `query:` et `passage:`. Aucun changement de base n'est effectué à l'import des modules.

Un dossier `pdfs/` vide lors d'une synchronisation publie une collection vide, tout en conservant l'ancienne génération. Un dossier manquant, un fichier illisible ou une erreur OCR interrompt la mise à jour. Les pages dont le texte reste trop court sont signalées dans le terminal et ne sont pas indexées ; un PDF sans aucun texte exploitable bloque la publication.

## Vérifications

```powershell
.\venv\Scripts\python.exe -m unittest test_rag -v
```

Les tests utilisent des PDF synthétiques, une base Chroma temporaire et des embeddings/LLM simulés. Ils vérifient l'OCR, la conservation des références, les préfixes E5, le contexte cité, l'historique, les mises à jour et leurs échecs, ainsi que le parcours Streamlit. Ils ne consomment pas l'API Groq et ne modifient pas les documents réels.

La qualité des réponses et de l'OCR doit encore être évaluée sur un jeu de questions et de pages annotées. `MIN_RELEVANCE_SCORE` est désactivé par défaut : calibrez-le avant utilisation et après migration de la base vers la distance cosinus. Les citations numérotées identifient les extraits transmis au modèle ; leur présence ne constitue pas une vérification automatique de chaque affirmation.

# Auto TikTok Travel

Un pipeline GitHub Actions minimal pour générer, monter et publier automatiquement des vidéos TikTok de voyage.
Ce dépôt est destiné à la démonstration : il crée actuellement un clip noir de 15 s (`output.mp4`) pour tester votre configuration.

## Démarrage rapide
1. Forkez ce dépôt.
2. Ajoutez les secrets (`OPENAI_KEY`, `RUNWAY_KEY`) même avec des valeurs de test.
3. Lancez le workflow **Auto‑TikTok** dans l’onglet *Actions*.
4. Téléchargez l’artefact `output.mp4` une fois le run terminé : s’il est présent, votre environnement GitHub Actions fonctionne.

Vous ajouterez ensuite les vraies clés et remplacerez la génération de la vidéo de test par les appels IA.
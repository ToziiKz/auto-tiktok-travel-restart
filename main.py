import os
import json
import time
import subprocess
import requests
from openai import OpenAI
# NOUVEL IMPORT : La bibliothèque officielle de RunwayML
from runwayml import RunwayML, TaskFailedError

# ───────── CONFIGURATION ─────────
DURATION = 15
ELEVENLABS_VOICE_ID = "TxGEqnHWrfWFTfGW9XjX"
OPENAI_MODEL = "gpt-4o-mini"
ELEVENLABS_MODEL = "eleven_multilingual_v2"
# Modèle Text-to-Video de Runway
RUNWAY_MODEL = "gen2" 

# Noms des fichiers
IDEA_FILE = "idea.json"
VIDEO_CLIP_FILE = "clip.mp4"
VOICE_FILE = "voice.mp3"
FINAL_VIDEO_FILE = "output.mp4"


# ───────── ÉTAPE 1 : GÉNÉRATION D’IDÉE (GPT) ─────────
def generate_idea() -> dict | None:
    """Génère une idée de vidéo avec OpenAI et la valide."""
    print("💡 Étape 1 : Génération de l'idée avec GPT...")
    try:
        client = OpenAI(api_key=os.environ["OPENAI_KEY"])
        prompt = (
            "Tu es un générateur JSON strict. Réponds UNIQUEMENT avec un objet JSON "
            'contenant les clés : "title", "description", "hashtags", "voice", "runway_prompt". '
            "La description doit faire entre 140 et 250 caractères. "
            "Les hashtags doivent être une chaîne de 5 mots-clés sans le #, séparés par des espaces."
        )
        res = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1,
            response_format={"type": "json_object"},
        )
        raw_content = res.choices[0].message.content
        idea = json.loads(raw_content)
        required_keys = ["title", "description", "hashtags", "voice", "runway_prompt"]
        if not all(key in idea for key in required_keys):
            print("❌ Erreur : Le JSON généré par OpenAI ne contient pas toutes les clés requises.")
            return None
        with open(IDEA_FILE, "w", encoding="utf-8") as f:
            json.dump(idea, f, ensure_ascii=False, indent=2)
        print(f"✅ Idée générée et sauvegardée : \"{idea['title']}\"")
        return idea
    except Exception as e:
        print(f"❌ Une erreur est survenue dans generate_idea : {e}")
        return None


# ───────── ÉTAPE 2 : VIDÉO IA (RUNWAY GEN-2) - MISE À JOUR ─────────
def generate_video(prompt: str) -> bool:
    """Génère une vidéo à partir d'un prompt avec la bibliothèque RunwayML."""
    print("🎞️  Étape 2 : Génération de la vidéo avec la bibliothèque RunwayML...")
    try:
        # Initialisation du client RunwayML avec la clé API
        client = RunwayML(api_key=os.environ["RUNWAY_KEY"])

        print(f"  - Envoi de la tâche au modèle '{RUNWAY_MODEL}'...")
        # Création de la tâche et attente du résultat.
        # La méthode .wait_for_task_output() remplace notre ancienne boucle "while".
        task = client.generate.create(
            model=RUNWAY_MODEL,
            # Le paramètre pour le texte est 'prompt'
            prompt=prompt,
            # Le paramètre pour la durée est 'duration'
            duration=DURATION,
        ).wait_for_task_output()

        print("  - Tâche Runway terminée. Statut :", task['status'])
        
        # Récupération de l'URL de la vidéo depuis la sortie de la tâche
        video_url = task['output']['video_url']

        # Téléchargement du clip
        print("  - Téléchargement du clip...")
        video_content = requests.get(video_url).content
        with open(VIDEO_CLIP_FILE, "wb") as f:
            f.write(video_content)

        print(f"✅ Vidéo '{VIDEO_CLIP_FILE}' prête.")
        return True

    # Gestion de l'erreur spécifique à la bibliothèque RunwayML
    except TaskFailedError as e:
        print("❌ La génération Runway a échoué.")
        print("  - Détails de l'erreur :", e.task_details)
        return False
    except KeyError:
        print("❌ Erreur : La clé API 'RUNWAY_KEY' n'est pas définie.")
        return False
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue dans generate_video : {e}")
        return False


# ───────── ÉTAPE 3 : VOIX-OFF IA (ELEVENLABS) ─────────
def generate_voice(text: str) -> bool:
    """Génère un fichier audio à partir du texte avec ElevenLabs."""
    print("🔊 Étape 3 : Génération de la voix-off avec ElevenLabs...")
    try:
        headers = {
            "xi-api-key": os.environ["ELEVEN_KEY"],
            "Content-Type": "application/json",
        }
        body = {"text": text, "model_id": ELEVENLABS_MODEL}
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        with open(VOICE_FILE, "wb") as f:
            f.write(response.content)
        print(f"✅ Voix-off '{VOICE_FILE}' prête.")
        return True
    except Exception as e:
        print(f"❌ Une erreur est survenue dans generate_voice : {e}")
        return False


# ───────── ÉTAPE 4 : FUSION FFmpeg ─────────
def merge_video_audio() -> bool:
    """Fusionne le clip vidéo et la voix-off avec FFmpeg."""
    print("🎬 Étape 4 : Fusion audio/vidéo avec FFmpeg...")
    if not os.path.exists(VIDEO_CLIP_FILE) or not os.path.exists(VOICE_FILE):
        print(f"❌ Erreur : Fichier d'entrée manquant ('{VIDEO_CLIP_FILE}' ou '{VOICE_FILE}').")
        return False
    try:
        command = [
            "ffmpeg", "-i", VIDEO_CLIP_FILE, "-i", VOICE_FILE,
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            FINAL_VIDEO_FILE, "-loglevel", "error", "-y",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"🏁 Vidéo finale '{FINAL_VIDEO_FILE}' générée !")
        return True
    except FileNotFoundError:
        print("❌ Erreur : 'ffmpeg' introuvable. Est-il installé et dans le PATH ?")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la fusion FFmpeg : {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Une erreur est survenue dans merge_video_audio : {e}")
        return False

# ───────── NETTOYAGE ─────────
def cleanup():
    """Supprime les fichiers intermédiaires."""
    print("🧹 Nettoyage des fichiers temporaires...")
    for file_path in [IDEA_FILE, VIDEO_CLIP_FILE, VOICE_FILE]:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"  - Supprimé : {file_path}")
        except OSError as e:
            print(f"⚠️ Impossible de supprimer {file_path}: {e}")


# ───────── PIPELINE COMPLET ─────────
def main():
    """Exécute le pipeline complet de création de vidéo."""
    print("🚀 Lancement du script d'automatisation TikTok IA 🚀")
    
    idea_data = generate_idea()
    if not idea_data:
        print("🛑 Arrêt du script : la génération d'idée a échoué.")
        return

    if not generate_video(idea_data["runway_prompt"]):
        print("🛑 Arrêt du script : la génération vidéo a échoué.")
        return

    if not generate_voice(idea_data["voice"]):
        print("🛑 Arrêt du script : la génération de la voix a échoué.")
        return

    if not merge_video_audio():
        print("🛑 Arrêt du script : la fusion a échoué.")
        return
        
    cleanup()
    
    print("\n🎉 Mission accomplie ! La vidéo est prête. 🎉")
    print(f"Titre : {idea_data['title']}")
    print(f"Description : {idea_data['description']}")
    print(f"Hashtags : {' '.join(['#' + tag for tag in idea_data['hashtags'].split()])}")


if __name__ == "__main__":
    main()

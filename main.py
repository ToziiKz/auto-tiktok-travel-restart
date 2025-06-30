import os
import json
import time
import subprocess
import requests
from openai import OpenAI

# ───────── CONFIGURATION ─────────
# Constantes et paramètres pour faciliter les modifications
DURATION = 15  # Durée de la vidéo IA (secondes)
ELEVENLABS_VOICE_ID = "TxGEqnHWrfWFTfGW9XjX"  # Voix FR "Rachel"
OPENAI_MODEL = "gpt-4o-mini"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# Noms des fichiers pour une gestion centralisée
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

        # Validation : on vérifie que toutes les clés nécessaires sont présentes
        required_keys = ["title", "description", "hashtags", "voice", "runway_prompt"]
        if not all(key in idea for key in required_keys):
            print("❌ Erreur : Le JSON généré par OpenAI ne contient pas toutes les clés requises.")
            return None

        with open(IDEA_FILE, "w", encoding="utf-8") as f:
            json.dump(idea, f, ensure_ascii=False, indent=2)

        print(f"✅ Idée générée et sauvegardée : \"{idea['title']}\"")
        return idea

    except (requests.exceptions.RequestException, OpenAI.APIError) as e:
        print(f"❌ Erreur lors de l'appel à l'API OpenAI : {e}")
        return None
    except KeyError:
        print("❌ Erreur : La clé API 'OPENAI_KEY' n'est pas définie dans les variables d'environnement.")
        return None
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue dans generate_idea : {e}")
        return None


# ───────── ÉTAPE 2 : VIDÉO IA (RUNWAY GEN-2) ─────────
def generate_video(prompt: str) -> bool:
    """Génère une vidéo à partir d'un prompt avec RunwayML."""
    print("🎞️  Étape 2 : Génération de la vidéo avec Runway...")
    try:
        headers = {
            "Authorization": f"Bearer {os.environ['RUNWAY_KEY']}",
            "Content-Type": "application/json",
        }
        body = {"prompt": prompt, "duration_seconds": DURATION}

        # 1. Lancer le job de génération (API v2)
        post_res = requests.post("https://api.runwayml.com/v2/generate", headers=headers, json=body)
        post_res.raise_for_status()
        job = post_res.json()
        task_id = job["id"]

        # 2. Polling pour vérifier le statut jusqu'au résultat (API v2)
        while True:
            time.sleep(8)
            get_res = requests.get(f"https://api.runwayml.com/v2/tasks/{task_id}", headers=headers)
            get_res.raise_for_status()
            job_status = get_res.json()
            
            status = job_status.get("status")
            print(f"  - Statut Runway : {status}")

            if status == "SUCCEEDED":
                video_url = job_status["output"]["video_url"]
                break
            elif status == "FAILED":
                error_message = job_status.get("error_message", "Erreur inconnue")
                print(f"❌ La génération Runway a échoué : {error_message}")
                return False

        # 3. Téléchargement du clip
        print("  - Téléchargement du clip...")
        video_content = requests.get(video_url).content
        with open(VIDEO_CLIP_FILE, "wb") as f:
            f.write(video_content)

        print(f"✅ Vidéo '{VIDEO_CLIP_FILE}' prête.")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP avec l'API Runway : {e}. Réponse : {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion avec l'API Runway : {e}")
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

        audio_content = response.content

        with open(VOICE_FILE, "wb") as f:
            f.write(audio_content)

        print(f"✅ Voix-off '{VOICE_FILE}' prête.")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP avec l'API ElevenLabs : {e}. Réponse : {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion avec l'API ElevenLabs : {e}")
        return False
    except KeyError:
        print("❌ Erreur : La clé API 'ELEVEN_KEY' n'est pas définie.")
        return False
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue dans generate_voice : {e}")
        return False


# ───────── ÉTAPE 4 : FUSION FFmpeg ─────────
def merge_video_audio() -> bool:
    """Fusionne le clip vidéo et la voix-off avec FFmpeg."""
    print("🎬 Étape 4 : Fusion audio/vidéo avec FFmpeg...")
    
    if not os.path.exists(VIDEO_CLIP_FILE) or not os.path.exists(VOICE_FILE):
        print(f"❌ Erreur : Un des fichiers d'entrée ('{VIDEO_CLIP_FILE}' ou '{VOICE_FILE}') est manquant.")
        return False

    try:
        command = [
            "ffmpeg",
            "-i", VIDEO_CLIP_FILE,
            "-i", VOICE_FILE,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            FINAL_VIDEO_FILE,
            "-loglevel", "error",
            "-y",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"🏁 Vidéo finale '{FINAL_VIDEO_FILE}' générée avec succès !")
        return True
    except FileNotFoundError:
        print("❌ Erreur : La commande 'ffmpeg' n'a pas été trouvée. Assurez-vous que FFmpeg est installé et dans le PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la fusion avec FFmpeg. Commande échouée.")
        print(f"   Erreur FFmpeg : {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Une erreur inattendue est survenue dans merge_video_audio : {e}")
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

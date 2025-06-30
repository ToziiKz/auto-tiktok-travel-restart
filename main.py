import os
import json
import time
import subprocess
import requests
from openai import OpenAI

# ───────── PARAMÈTRES GÉNÉRAUX ─────────
DURATION = 15                   # durée de la vidéo IA (secondes)

# ───────── ÉTAPE 1 : GÉNÉRATION D’IDÉE (GPT) ─────────
def generate_idea() -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_KEY"])

    prompt = (
        "Tu es un générateur JSON strict. Réponds UNIQUEMENT par un objet JSON "
        'avec les clés : "title", "description", "hashtags", "voice", "runway_prompt". '
        "Description 140-250 caractères, 5 hashtags sans # séparés par des espaces."
    )

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.1,
        response_format={"type": "json_object"}
    )

    raw = res.choices[0].message.content  # chaîne JSON
    idea = json.loads(raw)                # dict Python

    with open("idea.json", "w", encoding="utf-8") as f:
        json.dump(idea, f, ensure_ascii=False, indent=2)

    print("💡 Idée générée :", idea["title"])
    return idea

# ───────── ÉTAPE 2 : VIDÉO IA (RUNWAY GEN-2) ─────────
# ───────── ÉTAPE 2 : VIDÉO IA (RUNWAY GEN-2) ─────────
def generate_video(prompt: str) -> bool:
    """Génère une vidéo à partir d'un prompt avec RunwayML."""
    print("🎞️  Étape 2 : Génération de la vidéo avec Runway...")
    try:
        # NOTE : L'en-tête "Runway-Version" n'est plus nécessaire avec la v2 de l'API
        headers = {
            "Authorization": f"Bearer {os.environ['RUNWAY_KEY']}",
            "Content-Type": "application/json",
        }
        # NOTE : Le paramètre s'appelle maintenant "duration_seconds"
        # NOTE : L'URL de l'API est maintenant "/v2/generate"
        body = {"prompt": prompt, "duration_seconds": DURATION}

        # 1. Lancer le job de génération
        post_res = requests.post("https://api.runwayml.com/v2/generate", headers=headers, json=body)
        post_res.raise_for_status()
        job = post_res.json()
        task_id = job["id"]

        # 2. Polling pour vérifier le statut jusqu'au résultat
        # NOTE : L'URL pour vérifier le statut est maintenant "/v2/tasks/{task_id}"
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
def gen_voice(text: str) -> None:
    print("🔊  Génération voix-off…")

    voice_id = "TxGEqnHWrfWFTfGW9XjX"         # voix FR “Warm”
    headers = {
        "xi-api-key": os.environ["ELEVEN_KEY"],
        "Content-Type": "application/json"
    }
    body = {"text": text, "model_id": "eleven_multilingual_v2"}

    wav = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
        headers=headers,
        json=body
    ).content

    with open("voice.mp3", "wb") as f:
        f.write(wav)
    print("✅ voice.mp3 prêt")

# ───────── ÉTAPE 4 : FUSION FFmpeg ─────────
def merge() -> None:
    print("🎬  Fusion audio/vidéo…")
    subprocess.run([
        "ffmpeg", "-i", "clip.mp4", "-i", "voice.mp3",
        "-c:v", "copy", "-c:a", "aac", "-shortest", "output.mp4",
        "-loglevel", "quiet", "-y"
    ], check=True)
    print("🏁 output.mp4 généré")

# ───────── PIPELINE COMPLET ─────────
if __name__ == "__main__":
    # Étape 1 : Générer l'idée
    idea_data = generate_idea()
    if not idea_data:
        print("🛑 Arrêt du script : la génération d'idée a échoué.")
        exit()  # Quitte le script

    # Étape 2 : Générer la vidéo
    # Assurez-vous que les 2 lignes ci-dessous sont bien décalées de 4 espaces
    if not generate_video(idea_data["runway_prompt"]):
        print("🛑 Arrêt du script : la génération vidéo a échoué.")
        exit()  # Quitte le script

    # Étape 3 : Générer la voix
    # Assurez-vous que les 2 lignes ci-dessous sont bien décalées de 4 espaces
    if not generate_voice(idea_data["voice"]):
        print("🛑 Arrêt du script : la génération de la voix a échoué.")
        exit()  # Quitte le script

    # Étape 4 : Fusionner
    # Assurez-vous que les 2 lignes ci-dessous sont bien décalées de 4 espaces
    if not merge_video_audio():
        print("🛑 Arrêt du script : la fusion a échoué.")
        exit()  # Quitte le script
        
    # Si tout s'est bien passé, on nettoie et on affiche le résumé
    cleanup()
    
    print("\n🎉 Mission accomplie ! La vidéo est prête. 🎉")
    print(f"Titre : {idea_data['title']}")
    print(f"Description : {idea_data['description']}")
    print(f"Hashtags : {' '.join(['#' + tag for tag in idea_data['hashtags'].split()])}")

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
def gen_video(prompt: str) -> None:
    print("🎞️  Génération Runway…")

    headers = {
        "Authorization": f"Bearer {os.environ['RUNWAY_KEY']}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06"     # version API obligatoire
    }

    body = {"prompt": prompt, "duration": DURATION}

    # 1. Lancer le job
    job = requests.post(
        "https://api.runway.team/v1/image_to_video",
        headers=headers,
        json=body
    ).json()

    print("↪️  Réponse Runway :", job)        # log de debug

    # 2. Erreur immédiate ?
    if "id" not in job:
        raise RuntimeError(f"Runway error → {job}")

    job_id = job["id"]
    status = job["status"]

    # 3. Polling jusqu’au résultat
    while status not in ("succeeded", "failed"):
        time.sleep(6)
        status = requests.get(
            f"https://api.runwayml.com/v1/generate/video/{job_id}",
            headers=headers
        ).json()["status"]
        print("  status :", status)

    if status == "failed":
        raise RuntimeError("Runway generation failed")

    # 4. Téléchargement du clip
    url = requests.get(
        f"https://api.runwayml.com/v1/generate/video/{job_id}",
        headers=headers
    ).json()["video_url"]

    mp4 = requests.get(url).content
    with open("clip.mp4", "wb") as f:
        f.write(mp4)
    print("✅ clip.mp4 prêt")

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
    idea_data = generate_idea()
    gen_video(idea_data["runway_prompt"])
    gen_voice(idea_data["voice"])
    merge()

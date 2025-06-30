import os, json, subprocess, time, requests
from openai import OpenAI

# ---------- PARAMÈTRES GÉNÉRAUX ----------
DURATION = 15           # durée vidéo en secondes

# ---------- ÉTAPE 1 : générer l’idée ----------
def generate_idea():
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

    raw = res.choices[0].message.content     # ← chaîne JSON
    idea = json.loads(raw)                   # ← conversion en dict

    with open("idea.json", "w") as f:
        json.dump(idea, f, ensure_ascii=False, indent=2)

    print("💡 Idée générée :", idea["title"])
    return idea


# ---------- ÉTAPE 2 : générer la vidéo Runway ----------
def gen_video(prompt: str):
    print("🎞️  Génération Runway…")
    headers = {
        "Authorization": f"Bearer {os.environ['RUNWAY_KEY']}",
        "Content-Type": "application/json"
    }
    body = {"prompt": prompt, "duration": DURATION}
job = requests.post(
    "https://api.runwayml.com/v1/generate/video",
    headers=headers, json=body).json()

print("↪️  Réponse Runway :", job)          # ligne de debug

# si la clé “id” n’existe pas, on arrête tout de suite avec un message clair
if "id" not in job:
    raise RuntimeError(f"Runway error → {job}")

job_id = job["id"]


    status = job["status"]
    while status not in ("succeeded", "failed"):
        time.sleep(6)
        status = requests.get(
            f"https://api.runwayml.com/v1/generate/video/{job_id}",
            headers=headers).json()["status"]
        print("  status :", status)

    if status == "failed":
        raise RuntimeError("Runway generation failed")

    url = requests.get(
        f"https://api.runwayml.com/v1/generate/video/{job_id}",
        headers=headers).json()["video_url"]
    mp4 = requests.get(url).content
    open("clip.mp4", "wb").write(mp4)
    print("✅ clip.mp4 prêt")


# ---------- ÉTAPE 3 : générer la voix-off ElevenLabs ----------
def gen_voice(text: str):
    print("🔊  Génération voix-off…")
    voice_id = "TxGEqnHWrfWFTfGW9XjX"   # voix FR « Warm »
    headers = {
        "xi-api-key": os.environ["ELEVEN_KEY"],
        "Content-Type": "application/json"
    }
    body = {"text": text, "model_id": "eleven_multilingual_v2"}
    wav = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
        headers=headers, json=body).content
    open("voice.mp3", "wb").write(wav)
    print("✅ voice.mp3 prêt")


# ---------- ÉTAPE 4 : fusionner audio + vidéo ----------
def merge():
    print("🎬  Fusion audio/vidéo…")
    subprocess.run([
        "ffmpeg", "-i", "clip.mp4", "-i", "voice.mp3",
        "-c:v", "copy", "-c:a", "aac", "-shortest", "output.mp4",
        "-loglevel", "quiet", "-y"
    ])
    print("🏁 output.mp4 généré")


# ---------- PIPELINE COMPLET ----------
if __name__ == "__main__":
    idea = generate_idea()
    gen_video(idea["runway_prompt"])
    gen_voice(idea["voice"])
    merge()

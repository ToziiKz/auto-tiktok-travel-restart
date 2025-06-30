import os, json, subprocess, time, requests
from openai import OpenAI

# ---------- PARAMÈTRES ----------
DURATION = 15           # secondes
RES      = "1080x1920"  # portrait

# ---------- GPT : idée + script ----------
def generate_idea():
    client = OpenAI(api_key=os.environ["OPENAI_KEY"])
    prompt = (
        "Tu es un générateur JSON strict. Réponds UNIQUEMENT par un objet JSON "
        'avec les clés : "title", "description", "hashtags", "voice", "runway_prompt". '
        "Description 140-250 caractères, 5 hashtags séparés par des espaces."
    )
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.1,
        response_format={"type": "json_object"}   # ← ajoute cette ligne
    )
    idea = res.choices[0].message.model_dump()['content']  # déjà dict
    with open("idea.json", "w") as f:
        json.dump(idea, f, ensure_ascii=False, indent=2)
    print("💡 Idée :", idea["title"])
    return idea


# ---------- Runway Gen-2 ----------
def gen_video(prompt):
    print("🎞️  Génération Runway…")
    headers = {
        "Authorization": f"Bearer {os.environ['RUNWAY_KEY']}",
        "Content-Type": "application/json"
    }
    body = {"prompt": prompt, "duration": DURATION}
    job = requests.post(
        "https://api.runwayml.com/v1/generate/video",
        headers=headers, json=body).json()
    job_id = job["id"]

    status = job["status"]
    while status not in ("succeeded","failed"):
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
    open("clip.mp4","wb").write(mp4)
    print("✅ clip.mp4 prêt")

# ---------- ElevenLabs ----------
def gen_voice(text):
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
    open("voice.mp3","wb").write(wav)
    print("✅ voice.mp3 prêt")

# ---------- Fusion FFmpeg ----------
def merge():
    print("🎬  Fusion…")
    subprocess.run([
        "ffmpeg","-i","clip.mp4","-i","voice.mp3",
        "-c:v","copy","-c:a","aac","-shortest","output.mp4",
        "-loglevel","quiet","-y"
    ])
    print("🏁 output.mp4 généré")

# ---------- EXÉCUTION ----------
if __name__ == "__main__":
    idea = generate_idea()
    gen_video(idea["runway_prompt"])
    gen_voice(idea["voice"])
    merge()

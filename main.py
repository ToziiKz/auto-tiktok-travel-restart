import subprocess, os, sys

def create_black_clip():
    # Génère un clip noir de 15 s en 1080x1920
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "color=black:s=1080x1920:d=15", "output.mp4", "-y", "-loglevel", "quiet"])
    print("✔️ Clip noir généré : output.mp4")

if __name__ == "__main__":
    create_black_clip()
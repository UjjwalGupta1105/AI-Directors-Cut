import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
MUSIC_DIR = os.path.join(BASE_DIR, "music")

for _d in [UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR, MUSIC_DIR]:
    os.makedirs(_d, exist_ok=True)


def upload_path(filename: str) -> str:
    return os.path.join(UPLOADS_DIR, filename)


def output_path(filename: str) -> str:
    return os.path.join(OUTPUTS_DIR, filename)


def temp_path(filename: str) -> str:
    return os.path.join(TEMP_DIR, filename)


def find_background_music() -> str | None:
    for f in os.listdir(MUSIC_DIR):
        if f.endswith((".mp3", ".wav", ".ogg")):
            return os.path.join(MUSIC_DIR, f)
    return None

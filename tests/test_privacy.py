"""Privacy: secrets and user data must never be committed (except docs/demo fixtures)."""
import subprocess


def test_tracked_files_contain_no_private_data():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    tracked = [l for l in out.splitlines() if l.strip()]
    assert tracked, "expected a committed tree"
    bad = []
    audio_suffixes = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".mp4", ".mov")
    for path in tracked:
        low = path.lower()
        if path == "config.local.yaml" or low.endswith(".tflite"):
            bad.append(path)
        elif path.startswith("data/"):
            bad.append(path)
        elif low.endswith(audio_suffixes) and not path.startswith("docs/demo/"):
            bad.append(path)
    assert bad == [], f"private/generated files tracked in git: {bad}"

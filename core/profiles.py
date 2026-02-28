# core/profiles.py
import json
import os


class ProfileManager:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.profiles_dir, f"{name}.json")

    def save(self, name: str, data: dict) -> None:
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Profil '{name}' introuvable.")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_profiles(self) -> list[str]:
        return [f[:-5] for f in os.listdir(self.profiles_dir) if f.endswith(".json")]

    def delete(self, name: str) -> None:
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)

# core/profiles.py
import json
import os
import shutil


class ProfileManager:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)

    def _path(self, name: str, folder: str = "") -> str:
        if folder:
            return os.path.join(self.profiles_dir, folder, f"{name}.json")
        return os.path.join(self.profiles_dir, f"{name}.json")

    def save(self, name: str, data: dict, folder: str = "") -> None:
        path = self._path(name, folder)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, name: str, folder: str = "") -> dict:
        path = self._path(name, folder)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Profil '{name}' introuvable.")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def delete(self, name: str, folder: str = "") -> None:
        path = self._path(name, folder)
        if os.path.exists(path):
            os.remove(path)

    def list_tree(self) -> dict[str, list[str]]:
        """Return {folder_name: [profile_names]}. Key "" = root level. One level deep only."""
        tree: dict[str, list[str]] = {"": []}
        for entry in os.scandir(self.profiles_dir):
            if entry.is_file() and entry.name.endswith(".json"):
                tree[""].append(entry.name[:-5])
            elif entry.is_dir():
                tree[entry.name] = []
                for sub in os.scandir(entry.path):
                    if sub.is_file() and sub.name.endswith(".json"):
                        tree[entry.name].append(sub.name[:-5])
        return tree

    def create_folder(self, folder: str) -> None:
        os.makedirs(os.path.join(self.profiles_dir, folder), exist_ok=True)

    def delete_folder(self, folder: str) -> None:
        path = os.path.join(self.profiles_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)

    def list_profiles(self) -> list[str]:
        """Backward-compatible flat list of all profiles across all folders."""
        result = []
        for names in self.list_tree().values():
            result.extend(names)
        return result

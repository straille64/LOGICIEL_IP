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

    def rename(self, old_name: str, new_name: str, folder: str = "") -> None:
        """Renomme un profil JSON. Lève FileNotFoundError si old_name absent,
        FileExistsError si new_name existe déjà."""
        src = self._path(old_name, folder)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Profil '{old_name}' introuvable.")
        dst = self._path(new_name, folder)
        if os.path.exists(dst):
            raise FileExistsError(f"Un profil '{new_name}' existe déjà.")
        os.rename(src, dst)

    def rename_folder(self, old_name: str, new_name: str) -> None:
        """Renomme un dossier de profils. Lève FileNotFoundError si absent,
        FileExistsError si new_name existe déjà."""
        src = os.path.join(self.profiles_dir, old_name)
        if not os.path.isdir(src):
            raise FileNotFoundError(f"Dossier '{old_name}' introuvable.")
        dst = os.path.join(self.profiles_dir, new_name)
        if os.path.exists(dst):
            raise FileExistsError(f"Un dossier '{new_name}' existe déjà.")
        os.rename(src, dst)

    def move(self, name: str, from_folder: str, to_folder: str) -> None:
        """Déplace un profil JSON entre dossiers (from_folder="" ou to_folder="" = racine).
        Lève ValueError si source et destination sont identiques.
        Lève FileNotFoundError si le profil source est absent.
        Lève FileExistsError si la cible existe déjà."""
        src = self._path(name, from_folder)
        dst = self._path(name, to_folder)
        if src == dst:
            raise ValueError("La source et la destination sont identiques.")
        if not os.path.exists(src):
            raise FileNotFoundError(f"Profil '{name}' introuvable.")
        if os.path.exists(dst):
            raise FileExistsError(f"Un profil '{name}' existe déjà dans la destination.")
        os.makedirs(os.path.dirname(dst), exist_ok=True)  # no-op si dossier déjà existant
        shutil.move(src, dst)

    def list_profiles(self) -> list[str]:
        """Backward-compatible flat list of all profiles across all folders."""
        result = []
        for names in self.list_tree().values():
            result.extend(names)
        return result

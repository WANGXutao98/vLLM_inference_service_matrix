import os
import shutil
import pathlib

env_name = os.getenv("env", "local")
cfg_client = None

class FileConfiger():
    def __init__(self):
        self.cfg_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent / "conf"

    def get_config(self, key: str) -> str:
        filePath = f"{self.cfg_dir}/{key}.json"
        if not os.path.exists(filePath):
            return None
        with open(filePath, "r") as f:
            return f.read()

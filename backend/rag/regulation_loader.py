# Regulation Loader for RAG System
import json
import os

class RegulationLoader:
    def __init__(self, regulation_path: str):
        self.regulation_path = regulation_path
        self.regulations = self.load_regulations()

    def load_regulations(self):
        if not os.path.exists(self.regulation_path):
            raise FileNotFoundError(
                f"Regulation file not found: {self.regulation_path}"
            )
        with open(self.regulation_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_all(self):
        return self.regulations

    def search(self, keyword: str):
        """
        Simple keyword search inside regulations
        """
        results = []
        for r in self.regulations:
            # Use 'regulation' field for search, not 'text'
            if keyword.lower() in r.get("regulation", "").lower():
                results.append(r)
        return results

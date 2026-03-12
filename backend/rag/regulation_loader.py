# Regulation Loader for RAG System

import json
import os


class RegulationLoader:
    """
    Loads safety regulations from a JSON file
    and provides simple keyword search functionality.
    """

    def __init__(self, regulation_path: str):
        self.regulation_path = regulation_path
        self.regulations = self.load_regulations()

    def load_regulations(self):
        """
        Load regulations from JSON file
        """

        if not os.path.exists(self.regulation_path):
            raise FileNotFoundError(
                f"Regulation file not found: {self.regulation_path}"
            )

        try:
            with open(self.regulation_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if not isinstance(data, list):
                    raise ValueError("Regulation file must contain a list of regulations")

                return data

        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in regulation file")

    def get_all(self):
        """
        Return all regulations
        """
        return self.regulations

    def search(self, keyword: str):
        """
        Search regulations using keyword
        """

        results = []
        keyword = keyword.lower()

        for regulation in self.regulations:

            text = regulation.get("regulation", "").lower()

            if keyword in text:
                results.append(regulation)

        return results
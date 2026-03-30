from pathlib import Path
from typing import Iterable
import uuid

import chromadb
import pandas as pd


class Portfolio:
    def __init__(self, file_path=None):
        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent
        self.file_path = Path(file_path) if file_path else base_dir / "resource" / "my_portfolio.csv"
        self.vectorstore_dir = project_root / "vectorstore"
        self.data = pd.read_csv(self.file_path)
        self.chroma_client = chromadb.PersistentClient(path=str(self.vectorstore_dir))
        self.collection = self.chroma_client.get_or_create_collection(name="portfolio")
        self._portfolio_loaded = False

    def load_portfolio(self):
        if self._portfolio_loaded:
            return

        if not self.collection.count():
            for _, row in self.data.iterrows():
                self.collection.add(
                    documents=[row["Techstack"]],
                    metadatas=[{"links": row["Links"], "techstack": row["Techstack"]}],
                    ids=[str(uuid.uuid4())],
                )

        self._portfolio_loaded = True

    def query_links(self, skills):
        return [match["link"] for match in self.query_matches(skills)]

    def query_matches(self, skills):
        if skills is None:
            return []

        if isinstance(skills, str):
            skills = [item.strip() for item in skills.split(",")]
        elif not isinstance(skills, (list, tuple, set)):
            skills = [str(skills)]

        normalized_skills = [str(skill).strip() for skill in skills if skill and str(skill).strip()]
        if not normalized_skills:
            return []

        try:
            self.load_portfolio()
            results = self.collection.query(
                query_texts=[", ".join(normalized_skills)],
                n_results=min(3, len(self.data)),
            )
            metadatas = results.get("metadatas", [[]])
            matches = []
            for metadata in metadatas[0]:
                if not metadata:
                    continue
                link = str(metadata.get("links", "")).strip()
                techstack = str(metadata.get("techstack", "")).strip()
                if not link:
                    continue
                matches.append({"link": link, "techstack": techstack})
            return self._dedupe_matches(matches)
        except Exception:
            return self._fallback_query_links(normalized_skills)

    def _fallback_query_links(self, skills: list[str]) -> list[dict[str, str]]:
        target_skills = {skill.lower() for skill in skills}
        ranked_matches = []

        for _, row in self.data.iterrows():
            techstack_items = {
                item.strip().lower()
                for item in str(row["Techstack"]).split(",")
                if item.strip()
            }
            score = len(target_skills & techstack_items)
            if score:
                ranked_matches.append(
                    (score, {"link": row["Links"], "techstack": row["Techstack"]})
                )

        ranked_matches.sort(key=lambda item: item[0], reverse=True)
        return self._dedupe_matches(match for _, match in ranked_matches[:3])

    @staticmethod
    def _dedupe_links(links: Iterable[str]) -> list[str]:
        unique_links = []
        seen_links = set()

        for link in links:
            cleaned_link = str(link).strip()
            if not cleaned_link or cleaned_link in seen_links:
                continue
            seen_links.add(cleaned_link)
            unique_links.append(cleaned_link)

        return unique_links

    @staticmethod
    def _dedupe_matches(matches: Iterable[dict[str, str]]) -> list[dict[str, str]]:
        unique_matches = []
        seen_links = set()

        for match in matches:
            link = str(match.get("link", "")).strip()
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            unique_matches.append(
                {
                    "link": link,
                    "techstack": str(match.get("techstack", "")).strip(),
                }
            )

        return unique_matches

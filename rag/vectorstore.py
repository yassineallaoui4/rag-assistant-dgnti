"""Index persistant : publication après validation d'une nouvelle collection."""

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

import streamlit as st
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma

from config import DB_DIR, PDF_DIR, EMBEDDING_MODEL
from rag.pdf_loader import lister_pdfs, extraire_pages_pdf, decouper_documents

INDEX_VERSION = 2
_INDEX_LOCK = RLock()


class DocumentEmbeddings(Embeddings):
    """Chargement différé ; encodage initial conservé pour les anciennes collections."""

    def __init__(self, model_name: str, legacy: bool = False):
        self.model_name = model_name
        self.legacy = legacy

    def _encoder(self, texts: list[str], prefix: str) -> list[list[float]]:
        model = _charger_modele(self.model_name)
        use_e5 = "e5" in self.model_name.lower() and not self.legacy
        values = [prefix + t if use_e5 else t for t in texts]
        return model.encode(values, normalize_embeddings=not self.legacy).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encoder(texts, "passage: ")

    def embed_query(self, text: str) -> list[float]:
        return self._encoder([text], "query: ")[0]


@st.cache_resource
def _charger_modele(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


@st.cache_resource
def get_embeddings(model_name: str = EMBEDDING_MODEL, legacy: bool = False) -> DocumentEmbeddings:
    return DocumentEmbeddings(model_name, legacy)


def _manifest_path() -> Path:
    return DB_DIR / "active_index.json"


def _lire_manifest() -> dict | None:
    path = _manifest_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("version") != INDEX_VERSION or not isinstance(data.get("files"), dict)
            or not isinstance(data.get("model"), str)
            or not isinstance(data.get("collection"), str)):
        raise ValueError("Description de la base invalide. Restaurez active_index.json depuis une sauvegarde.")
    return data


def base_existe() -> bool:
    return (DB_DIR / "chroma.sqlite3").is_file()


@st.cache_resource
def _charger_collection(directory: str, collection: str, model: str, legacy: bool) -> Chroma:
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=directory, settings=Settings(anonymized_telemetry=False))
    client.get_collection(collection)
    return Chroma(client=client, collection_name=collection,
                  embedding_function=get_embeddings(model, legacy))


def charger_base() -> Chroma | None:
    if not base_existe():
        return None
    manifest = _lire_manifest()
    return _charger_collection(
        str(DB_DIR), manifest["collection"] if manifest else "langchain",
        manifest["model"] if manifest else EMBEDDING_MODEL, legacy=manifest is None,
    )


def _empreintes() -> dict[str, str]:
    if not PDF_DIR.is_dir():
        raise FileNotFoundError("Le dossier pdfs/ est introuvable.")
    result = {}
    for name in lister_pdfs():
        with (PDF_DIR / name).open("rb") as stream:
            result[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def _publier_manifest(manifest: dict) -> None:
    temp = DB_DIR / f"active_index.{uuid4().hex}.tmp"
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, _manifest_path())
    finally:
        if temp.exists():
            temp.unlink()


def _construire_index(files: dict[str, str], previous: dict | None, force: bool) -> Chroma:
    reusable: dict[str, list[Document]] = {}
    if previous and not force:
        old = charger_base().get()
        for text, meta in zip(old["documents"], old["metadatas"]):
            name = (meta or {}).get("source")
            if name in files and previous["files"].get(name) == files[name]:
                reusable.setdefault(name, []).append(Document(page_content=text, metadata=meta))

    chunks = []
    progress = st.progress(0.0, text="Préparation des documents…")
    try:
        for index, name in enumerate(files):
            docs = reusable.get(name)
            if not docs:
                docs = decouper_documents(extraire_pages_pdf(name))
            if not docs:
                raise ValueError(f"Aucun texte exploitable dans {name}. La base précédente est conservée.")
            chunks.extend(docs)
            progress.progress((index + 1) / len(files), text=f"Document {index + 1}/{len(files)}")
    finally:
        progress.empty()

    name = f"dsit_{uuid4().hex}"
    from chromadb.config import Settings
    db = Chroma(collection_name=name, persist_directory=str(DB_DIR),
                embedding_function=get_embeddings(),
                client_settings=Settings(anonymized_telemetry=False, is_persistent=True),
                collection_metadata={"hnsw:space": "cosine"})
    try:
        for start in range(0, len(chunks), 128):
            db.add_documents(chunks[start:start + 128])
        if len(db.get(include=[])["ids"]) != len(chunks):
            raise RuntimeError("Le nombre de passages indexés est incomplet.")
        if _empreintes() != files:
            raise RuntimeError("Les PDF ont changé pendant l'indexation. Relancez la mise à jour.")
        _publier_manifest({"version": INDEX_VERSION, "collection": name,
                           "model": EMBEDDING_MODEL, "files": files, "chunks": len(chunks)})
    except Exception:
        db.delete_collection()
        raise
    return db


def reconstruire_base() -> Chroma:
    """Reconstruit dans une nouvelle collection ; conserve l'ancienne génération."""
    with _INDEX_LOCK:
        files = _empreintes()
        if not files:
            raise ValueError("Aucun PDF à indexer.")
        return _construire_index(files, _lire_manifest(), force=True)


def synchroniser_base() -> Chroma:
    """Détecte ajouts, suppressions et modifications par empreinte SHA-256."""
    with _INDEX_LOCK:
        files = _empreintes()
        previous = _lire_manifest()
        if (previous and previous["files"] == files
                and previous["model"] == EMBEDDING_MODEL):
            st.info("La base est à jour.")
            return charger_base()
        if not files and not base_existe():
            raise ValueError("Aucun PDF à indexer.")
        return _construire_index(files, previous, force=False)


def obtenir_base() -> Chroma | None:
    return charger_base()

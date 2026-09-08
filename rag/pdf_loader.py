"""
rag/pdf_loader.py
-----------------
Extraction de texte depuis les PDFs (natif + OCR Tesseract pour les pages scannées).
Pipeline OCR optimisé pour les courriers arabes scannés :
  - Rendu directement en niveaux de gris via PyMuPDF (colorspace=csGRAY)
  - DPI élevé (×4 = ~288 DPI)
  - Netteté ×2 + contraste ×1.5
  - Binarisation noir/blanc pur (mode "1") — format préféré par Tesseract
  - Moteur disponible (--oem 3) + détection auto mise en page (--psm 3)
  - OCR bilingue fra+ara pour préserver les courriers mixtes
  - Validation lisibilité du texte natif (filtre encodages cassés)
  - Nettoyage du bruit OCR avant indexation
"""

import re
import logging

import fitz
import pytesseract
import streamlit as st
from PIL import Image, ImageEnhance
from langchain_core.documents import Document

from config import (
    PDF_DIR,
    MIN_PAGE_CHARS,
    OCR_DPI_MATRIX,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TESSERACT_CMD,
    OCR_TIMEOUT,
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configuration Tesseract optimisée pour l'arabe administratif
# --oem 3 : moteur choisi selon les données Tesseract installées
# --psm 3 : détection automatique de la mise en page (colonnes, blocs, en-têtes)
_TESSERACT_CONFIG = r"--oem 3 --psm 3"


def lister_pdfs() -> list[str]:
    """Retourne la liste des noms de fichiers PDF présents dans PDF_DIR."""
    return sorted(p.name for p in PDF_DIR.glob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def _texte_est_lisible(texte: str) -> bool:
    """
    Écarte les extractions vides ou présentant des caractères invalides.
    Ce filtre ne peut pas reconnaître tous les encodages incorrects ;
    il préserve le texte français aussi bien que le texte arabe.
    """
    if len(texte) < MIN_PAGE_CHARS:
        return False

    visibles = [c for c in texte if not c.isspace()]
    if not visibles:
        return False
    invalides = sum(c == "\ufffd" or "\ue000" <= c <= "\uf8ff" or ord(c) < 32 for c in visibles)
    utiles = sum(c.isalnum() for c in visibles)
    return invalides / len(visibles) < 0.05 and utiles / len(visibles) > 0.5


def _detecter_langue(texte: str) -> str:
    """Utilise les deux langues, même sans texte natif exploitable."""
    # Un scan ne permet pas de déduire sa langue du texte natif absent.
    # Garder les deux langues préserve aussi les en-têtes bilingues.
    return "fra+ara"


def _preparer_image_ocr(img: Image.Image) -> Image.Image:
    """
    Prétraitement de l'image avant OCR :
    1. Netteté ×2   — renforce les contours des caractères arabes
    2. Contraste ×1.5 — améliore la séparation texte/fond
    3. Binarisation noir/blanc pur (mode "1") — format préféré par Tesseract
    Note : l'image reçue est déjà en niveaux de gris (csGRAY depuis PyMuPDF).
    """
    img_sharp = ImageEnhance.Sharpness(img).enhance(2.0)
    img_contrast = ImageEnhance.Contrast(img_sharp).enhance(1.5)
    img_bw = img_contrast.convert("1", dither=Image.Dither.NONE)
    return img_bw


def _nettoyer_texte_ocr(texte: str) -> str:
    """
    Nettoie le bruit typique produit par Tesseract sur des scans arabes :
    - Supprime les caractères de contrôle bidi et marks invisibles
    - Filtre les lignes sans caractères utiles, en conservant les références courtes
    - Réduit les espaces multiples
    """
    # Supprimer les caractères de contrôle bidi et marks Unicode invisibles
    texte = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]", "", texte)

    # Filtrer les lignes trop courtes ou sans caractères arabes/latins réels
    lignes = texte.split("\n")
    lignes_propres = []
    for ligne in lignes:
        chars_utiles = sum(
            1
            for c in ligne
            if ("\u0600" <= c <= "\u06FF") or c.isalpha() or c.isdigit()
        )
        if chars_utiles >= 1:
            lignes_propres.append(ligne)

    texte_propre = "\n".join(lignes_propres)
    texte_propre = re.sub(r" {3,}", "  ", texte_propre)
    return texte_propre.strip()


def extraire_pages_pdf(nom_fichier: str) -> list[Document]:
    """
    Extrait le texte de chaque page d'un PDF.
    - Pages natives lisibles  : extraction directe via PyMuPDF.
    - Pages scannées ou encodage cassé : pipeline OCR complet via Tesseract.
    Retourne la liste des Documents LangChain avec métadonnées source/page.
    """
    chemin = PDF_DIR / nom_fichier
    if chemin.resolve().parent != PDF_DIR.resolve():
        raise ValueError("Le PDF doit appartenir au dossier documentaire.")
    documents = []
    pages_ocr_ok = 0
    pages_ocr_echec = 0

    # ── Étape 1 : extraction native ──────────────────────────────────────────
    try:
        with fitz.open(chemin) as pdf:
            pages_natives = [
                (i, page.get_text("text").strip()) for i, page in enumerate(pdf)
            ]
    except Exception as e:
        raise RuntimeError(f"Impossible d'ouvrir le PDF {nom_fichier}.") from e

    # Pages à traiter par OCR : scannées OU texte natif illisible (encodage cassé)
    pages_scannees = [i for i, t in pages_natives if not _texte_est_lisible(t)]

    # ── Étape 2 : OCR sur les pages scannées ────────────────────────────────
    ocr_results: dict[int, str] = {}
    erreurs_ocr = []
    if pages_scannees:
        with fitz.open(chemin) as pdf:
            for i in pages_scannees:
                try:
                    # Rendu directement en niveaux de gris à haute résolution
                    pix = pdf[i].get_pixmap(
                        matrix=fitz.Matrix(OCR_DPI_MATRIX, OCR_DPI_MATRIX),
                        colorspace=fitz.csGRAY,
                    )
                    img_raw = Image.frombytes("L", (pix.width, pix.height), pix.samples)

                    # Prétraitement : netteté + contraste + binarisation N/B
                    img_traitee = _preparer_image_ocr(img_raw)

                    # Détection langue + OCR LSTM
                    lang = _detecter_langue(pages_natives[i][1])
                    texte_ocr = pytesseract.image_to_string(
                        img_traitee, lang=lang, config=_TESSERACT_CONFIG,
                        timeout=OCR_TIMEOUT,
                    ).strip()

                    ocr_results[i] = texte_ocr

                    if len(_nettoyer_texte_ocr(texte_ocr)) >= MIN_PAGE_CHARS:
                        pages_ocr_ok += 1
                    else:
                        pages_ocr_echec += 1
                        print(
                            f"[OCR] Page {i} de {nom_fichier} : "
                            f"texte insuffisant ({len(texte_ocr)} chars) — scan trop dégradé ?"
                        )
                except Exception:
                    erreurs_ocr.append(i + 1)
                    logging.getLogger(__name__).exception("Échec OCR : %s, page %s", nom_fichier, i + 1)

    if erreurs_ocr:
        raise RuntimeError(f"OCR incomplet pour {nom_fichier}, pages {erreurs_ocr}. La base précédente est conservée.")

    # ── Étape 3 : assemblage et nettoyage des Documents ─────────────────────
    for i, texte_natif in pages_natives:
        texte_brut = ocr_results.get(i, texte_natif if _texte_est_lisible(texte_natif) else "")
        texte = _nettoyer_texte_ocr(texte_brut)
        if len(texte) >= MIN_PAGE_CHARS:
            documents.append(
                Document(
                    page_content=texte,
                    metadata={"source": nom_fichier, "page": i},
                )
            )

    # Log de diagnostic dans le terminal
    total = len(pages_natives)
    natif = total - len(pages_scannees)
    print(
        f"[PDF] {nom_fichier} | {total} pages | "
        f"{natif} natives | {pages_ocr_ok} OCR OK | {pages_ocr_echec} OCR échec | "
        f"{len(documents)} documents extraits"
    )

    return documents


def decouper_documents(documents: list[Document]) -> list[Document]:
    """Découpe les documents en chunks avec chevauchement."""
    # Cette dépendance charge des modules lourds : uniquement lors de l'indexation.
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(documents)


def construire_chunks(pdf_names: list[str]) -> list[Document]:
    """
    Parcourt la liste de PDFs, extrait et découpe leur contenu.
    Affiche une barre de progression Streamlit + résumé final.
    """
    chunks: list[Document] = []
    pdfs_vides: list[str] = []
    progress = st.progress(0, text="Indexation…")

    for idx, nom in enumerate(pdf_names):
        progress.progress(
            (idx + 1) / len(pdf_names),
            text=f"Indexation ({idx + 1}/{len(pdf_names)}) : {nom}",
        )
        docs = extraire_pages_pdf(nom)
        if not docs:
            pdfs_vides.append(nom)
            continue
        chunks.extend(decouper_documents(docs))

    progress.empty()

    if pdfs_vides:
        st.warning(
            f"⚠️ {len(pdfs_vides)} PDF(s) sans texte extrait "
            f"(scan trop dégradé ou fichier vide) : "
            + ", ".join(pdfs_vides[:5])
            + ("…" if len(pdfs_vides) > 5 else "")
        )

    valides = len(pdf_names) - len(pdfs_vides)
    st.info(f"📊 {len(chunks)} chunks extraits depuis {valides}/{len(pdf_names)} PDF(s).")
    print(
        f"[INDEX] Total : {len(chunks)} chunks | {valides} PDFs OK | {len(pdfs_vides)} PDFs vides"
    )

    return chunks

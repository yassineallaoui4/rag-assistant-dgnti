"""Tests hors ligne. Aucun accès aux PDF, à la base réelle ou à Groq."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import fitz
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from rag import pdf_loader as pdf
from rag import qa_engine as qa
from rag import vectorstore as vs


class OCRTests(unittest.TestCase):
    def test_native_french_and_arabic(self):
        self.assertTrue(pdf._texte_est_lisible("Veuillez trouver ci-joint le courrier concernant la réunion de service."))
        self.assertTrue(pdf._texte_est_lisible("مراسلة إدارية تتعلق بتنظيم الاجتماع في مقر العمالة"))
        self.assertFalse(pdf._texte_est_lisible("\ufffd" * 30))
        self.assertEqual(pdf._detecter_langue(""), "fra+ara")

    def test_short_reference_is_preserved(self):
        self.assertIn("\n42\n", pdf._nettoyer_texte_ocr("Référence\n42\nCourrier administratif"))

    def test_native_pdf_does_not_call_ocr(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pdf, "PDF_DIR", Path(directory)):
            with fitz.open() as document:
                document.new_page().insert_text((40, 40), "Courrier administratif concernant la reunion de service.")
                document.save(Path(directory) / "courrier.PDF")
            with patch.object(pdf.pytesseract, "image_to_string") as ocr:
                docs = pdf.extraire_pages_pdf("courrier.PDF")
                ocr.assert_not_called()
            self.assertEqual(pdf.lister_pdfs(), ["courrier.PDF"])
            self.assertEqual(docs[0].metadata, {"source": "courrier.PDF", "page": 0})

    def test_ocr_failure_does_not_skip_remaining_pages(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pdf, "PDF_DIR", Path(directory)):
            with fitz.open() as document:
                document.new_page(width=40, height=40)
                document.new_page(width=40, height=40)
                document.save(Path(directory) / "scan.pdf")
            with patch.object(pdf.pytesseract, "image_to_string", side_effect=[RuntimeError("timeout"), "Texte administratif de la deuxième page."]) as ocr:
                with self.assertRaisesRegex(RuntimeError, "pages \\[1\\]"):
                    pdf.extraire_pages_pdf("scan.pdf")
                self.assertEqual(ocr.call_count, 2)


class AnswerTests(unittest.TestCase):
    def test_context_budget_and_sources_match(self):
        docs = [Document(page_content="a" * 100, metadata={"source": "a.pdf", "page": 0}),
                Document(page_content="b" * 100, metadata={"source": "b.pdf", "page": 1})]
        with patch.object(qa, "MAX_CONTEXT_CHARS", 70):
            context, sources = qa._construire_contexte(docs)
        self.assertLessEqual(len(context), 70)
        self.assertEqual(len(sources), 1)
        self.assertIn("[1] a.pdf — page 1", context)
        self.assertIn(sources[0].page_content, context)

    def test_empty_results_refuse_in_arabic_without_llm(self):
        db = MagicMock()
        db.similarity_search.return_value = []
        with patch.object(qa, "get_llm") as llm:
            answer, sources = qa.poser_question(db, "ما تاريخ الرسالة؟", 4, "Concis")
        llm.assert_not_called()
        self.assertIn("لم أعثر", answer)
        self.assertEqual(sources, [])

    def test_followup_rewritten_and_history_sent(self):
        db = MagicMock()
        db.similarity_search.return_value = [Document(page_content="La réunion aura lieu lundi.", metadata={"source": "a.pdf", "page": 1})]
        llm = MagicMock()
        llm.invoke.side_effect = [SimpleNamespace(content="Quelle est la date de la réunion ?"), SimpleNamespace(content="Lundi [1].")]
        with patch.object(qa, "get_llm", return_value=llm):
            answer, sources = qa.poser_question(db, "Et sa date ?", 4, "Concis", [{"question": "Une réunion est-elle prévue ?", "reponse": "Oui."}])
        db.similarity_search.assert_called_once_with("Quelle est la date de la réunion ?", k=4)
        messages = llm.invoke.call_args_list[1].args[0]
        self.assertEqual(messages[0].type, "system")
        self.assertEqual(messages[1].content, "Une réunion est-elle prévue ?")
        self.assertIn("[1] a.pdf — page 2", messages[-1].content)
        self.assertEqual(answer, "Lundi [1].")
        self.assertEqual(len(sources), 1)

    def test_history_bounded(self):
        with patch.object(qa, "MAX_HISTORY_CHARS", 10):
            messages = qa._historique_messages([{"question": "old", "reponse": "long answer"}, {"question": "new", "reponse": "yes"}])
        self.assertEqual([m.content for m in messages], ["new", "yes"])


class EmbeddingTests(unittest.TestCase):
    def test_prefixes_and_legacy_compatibility(self):
        model = MagicMock()
        model.encode.return_value.tolist.return_value = [[1.0, 0.0]]
        with patch.object(vs, "_charger_modele", return_value=model):
            encoder = vs.DocumentEmbeddings("intfloat/multilingual-e5-base")
            encoder.embed_query("question")
            model.encode.assert_called_with(["query: question"], normalize_embeddings=True)
            encoder.embed_documents(["texte"])
            model.encode.assert_called_with(["passage: texte"], normalize_embeddings=True)
            vs.DocumentEmbeddings("intfloat/multilingual-e5-base", legacy=True).embed_query("question")
            model.encode.assert_called_with(["question"], normalize_embeddings=False)


class ServiceErrorTests(unittest.TestCase):
    def test_model_not_found_is_actionable_without_raw_response(self):
        import httpx
        from groq import NotFoundError
        response = httpx.Response(404, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))
        exc = NotFoundError("private-server-detail", response=response,
                            body={"error": {"code": "model_not_found"}})
        message = qa.message_erreur(exc)
        self.assertIn("GROQ_MODEL", message)
        self.assertIn(qa.MODEL, message)
        self.assertNotIn("private-server-detail", message)

    def test_quota_and_authentication_are_distinguished(self):
        import httpx
        from groq import AuthenticationError, RateLimitError
        for status, error_type, expected in [(401, AuthenticationError, "GROQ_API_KEY"), (429, RateLimitError, "quotas")]:
            response = httpx.Response(status, request=httpx.Request("POST", "https://api.groq.com"))
            self.assertIn(expected, qa.message_erreur(error_type("private detail", response=response, body={})))

    def test_local_search_failure_does_not_blame_groq(self):
        db = MagicMock()
        db.similarity_search.side_effect = ValueError("Embedding dimension mismatch")
        with patch.object(qa, "get_llm") as llm:
            with self.assertRaises(qa.ErreurRecherche) as raised:
                qa.poser_question(db, "Question", 4, "Concis")
            llm.assert_not_called()
        self.assertIn("embedding", qa.message_erreur(raised.exception))


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[1.0, float(len(t) % 7) / 7, 0.2] for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class IndexTests(unittest.TestCase):
    """Vraie base Chroma temporaire ; seuls OCR et embeddings sont simulés."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp.name)
        self.pdfs = self.root / "pdfs"
        self.pdfs.mkdir()
        self.dbdir = self.root / "db"
        self.patches = [patch.object(vs, "DB_DIR", self.dbdir), patch.object(vs, "PDF_DIR", self.pdfs),
                        patch.object(pdf, "PDF_DIR", self.pdfs), patch.object(vs, "get_embeddings", return_value=FakeEmbeddings()),
                        patch.object(vs, "extraire_pages_pdf", side_effect=lambda name: [Document(page_content=(self.pdfs / name).read_text(), metadata={"source": name, "page": 0})])]
        for item in self.patches:
            item.start()
        (self.pdfs / "a.pdf").write_text("Premier texte administratif assez long.")

    def tearDown(self):
        vs._charger_collection.clear()
        from chromadb.api.shared_system_client import SharedSystemClient
        system = SharedSystemClient._identifier_to_system.pop(str(self.dbdir), None)
        if system:
            system.stop()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_replaced_pdf_updates_and_old_collection_survives(self):
        old = vs.synchroniser_base()
        original_name = vs._lire_manifest()["collection"]
        (self.pdfs / "a.pdf").write_text("Nouveau texte administratif de remplacement.")
        new = vs.synchroniser_base()
        self.assertNotEqual(vs._lire_manifest()["collection"], original_name)
        self.assertIn("Nouveau", new.get()["documents"][0])
        self.assertIn("Premier", old.get()["documents"][0])
        self.assertIn("Nouveau", vs.charger_base().get()["documents"][0])

    def test_failed_embedding_keeps_active_index(self):
        vs.synchroniser_base()
        original = vs._manifest_path().read_bytes()
        (self.pdfs / "a.pdf").write_text("Nouveau courrier administratif pour le test.")
        with patch.object(FakeEmbeddings, "embed_documents", side_effect=RuntimeError("embedding unavailable")):
            with self.assertRaisesRegex(RuntimeError, "embedding unavailable"):
                vs.synchroniser_base()
        self.assertEqual(vs._manifest_path().read_bytes(), original)
        self.assertIn("Premier", vs.charger_base().get()["documents"][0])

    def test_unchanged_skips_extraction_and_empty_folder_publishes_empty(self):
        old = vs.synchroniser_base()
        original = vs._manifest_path().read_bytes()
        with patch.object(vs, "extraire_pages_pdf") as extract:
            vs.synchroniser_base()
            extract.assert_not_called()
        self.assertEqual(vs._manifest_path().read_bytes(), original)
        (self.pdfs / "a.pdf").unlink()
        empty = vs.synchroniser_base()
        self.assertEqual(empty.get()["ids"], [])
        self.assertEqual(len(old.get()["ids"]), 1)

    def test_failed_ocr_preserves_previous_generation(self):
        vs.synchroniser_base()
        original = vs._manifest_path().read_bytes()
        (self.pdfs / "b.pdf").write_text("Nouveau PDF.")
        with patch.object(vs, "extraire_pages_pdf", side_effect=RuntimeError("OCR unavailable")):
            with self.assertRaisesRegex(RuntimeError, "OCR unavailable"):
                vs.synchroniser_base()
        self.assertEqual(vs._manifest_path().read_bytes(), original)


class InterfaceTests(unittest.TestCase):
    def test_empty_app_and_chat_roundtrip(self):
        from streamlit.testing.v1 import AppTest
        import ui.sidebar as sidebar
        import os
        app_path = str(Path(__file__).with_name("app.py"))
        with patch.object(sidebar, "obtenir_base", return_value=None), patch("dotenv.load_dotenv"), patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            app = AppTest.from_file(app_path).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.chat_input[0].disabled)
        db = MagicMock()
        db.get.return_value = {"ids": ["1"]}
        db.similarity_search.return_value = [Document(page_content="Réunion lundi.", metadata={"source": "test.pdf", "page": 0})]
        llm = MagicMock()
        llm.invoke.return_value = SimpleNamespace(content="La réunion est lundi [1].")
        with patch.object(sidebar, "obtenir_base", return_value=db), patch.object(qa, "get_llm", return_value=llm), patch("dotenv.load_dotenv"), patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            app = AppTest.from_file(app_path).run(timeout=20)
            app.chat_input[0].set_value("Quand est la réunion ?").run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state["history"]), 1)
            self.assertEqual(app.session_state["history"][0]["sources"][0]["fichier"], "test.pdf")


if __name__ == "__main__":
    unittest.main()

"""Tests de bout en bout avec un règlement fictif et un modèle simulé.
Lancer : python -m unittest discover tests"""
import csv
import tempfile
import unittest
from pathlib import Path

from rag.assistant import Assistant
from rag.evaluation import est_abstention, evaluer, juger, lois_citees
from rag.ingestion import controle_qualite, ingerer
from rag.modele import Modele
from rag.rapport import ecrire_rapport
from rag.recherche import IndexBM25
from tests.fixtures.creer_reglement_fictif import generer


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = Path(tempfile.mkdtemp())
        source = generer(cls.dossier / "reglement_fictif.txt")
        cls.extraits = ingerer(source, cls.dossier / "extraits.jsonl")
        cls.index = IndexBM25(cls.extraits)

    def test_les_17_lois_sont_detectees(self):
        lois = {e["loi"] for e in self.extraits}
        self.assertEqual(lois - {0}, set(range(1, 18)))
        _, alertes = controle_qualite(self.extraits)
        self.assertEqual(alertes, [])

    def test_sommaire_et_glossaire_hors_des_lois(self):
        sommaire = [e for e in self.extraits if "Sommaire" in e["texte"]]
        glossaire = [e for e in self.extraits if "Glossaire" in e["texte"]]
        self.assertTrue(sommaire and all(e["loi"] == 0 for e in sommaire))
        self.assertTrue(glossaire and all(e["loi"] == 0 for e in glossaire))

    def test_paragraphe_numerote_ne_change_pas_de_loi(self):
        # « 2. Marquage » dans la Loi 1 ne doit pas être pris pour la Loi 2
        marquage = [e for e in self.extraits if "Marquage" in e["texte"]]
        self.assertTrue(marquage and all(e["loi"] == 1 for e in marquage))

    def test_recherche_trouve_la_bonne_loi(self):
        cas = {
            "Combien de temps dure une rencontre et la pause ?": 7,
            "À quelle distance les adversaires restent-ils lors d'une rentrée de touche ?": 15,
            "Peut-on être hors-jeu dans sa propre moitié ?": 11,
        }
        for question, loi in cas.items():
            premiers = self.index.chercher(question, k=4)
            self.assertIn(loi, [e["loi"] for e in premiers], question)

    def test_analyse_des_reponses(self):
        self.assertEqual(lois_citees("Voir [Loi 7] et la loi 12, pas la loi 45."), [7, 12])
        self.assertTrue(est_abstention("Je ne trouve pas cette information dans les Lois du Jeu."))
        self.assertFalse(est_abstention("Deux périodes de 45 minutes [Loi 7]."))

    def test_reponse_en_morceaux(self):
        from rag.modele import extraire_texte
        contenu = [{"type": "thinking", "thinking": [{"type": "text", "text": "Je réfléchis…"}]},
                   {"type": "text", "text": "Huit secondes [Loi 12]."}]
        self.assertEqual(extraire_texte(contenu), "Huit secondes [Loi 12].")
        self.assertEqual(extraire_texte("  Texte simple. "), "Texte simple.")

    def test_csv_enregistre_par_excel(self):
        from rag.evaluation import charger_questions
        contenu = ("id;categorie;type;question;reponse_attendue;loi_attendue;a_verifier;valide\r\n"
                   "q01;Durée;dans_le_document;Quelle est la durée d'un match ?;Deux périodes de 45 minutes.;7;;oui\r\n"
                   "q02;Terrain;dans_le_document;Rayon du cercle central ?;9,15 m.;1;;\r\n")
        variantes = [(contenu, enc) for enc in ("cp1252", "mac_roman", "utf-8")]
        variantes.append((contenu.replace(";", "\t"), "utf-16"))   # « Texte Unicode » d'Excel
        variantes.append((contenu.replace(";", "\t"), "mac_roman"))
        for texte, enc in variantes:
            chemin = Path(tempfile.mkdtemp()) / "questions.csv"
            chemin.write_bytes(texte.encode(enc))
            toutes = charger_questions(chemin)
            self.assertEqual(len(toutes), 2, enc)
            self.assertEqual(toutes[0]["categorie"], "Durée", enc)
            self.assertEqual(toutes[1]["reponse_attendue"], "9,15 m.", enc)
            self.assertEqual([q["id"] for q in charger_questions(chemin, True)], ["q01"], enc)

    def test_classeur_excel_nomme_csv(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl non installé (lecture des classeurs Excel facultative)")
        from rag.evaluation import charger_questions
        wb = Workbook()
        ws = wb.active
        ws.append(["id", "categorie", "type", "question", "reponse_attendue", "loi_attendue", "a_verifier", "valide"])
        ws.append(["q01", "Durée", "dans_le_document", "Durée d'un match ?", "Deux périodes de 45 minutes.", 7, None, "oui"])
        chemin = Path(tempfile.mkdtemp()) / "questions.csv"
        wb.save(chemin)
        q = charger_questions(chemin, True)
        self.assertEqual(q[0]["question"], "Durée d'un match ?")
        self.assertEqual(q[0]["loi_attendue"], "7")

    def test_juge_illisible(self):
        class JugeBavard:
            def repondre(self, s, m):
                return "Je pense que c'est plutôt bien."
        verdict, _ = juger(JugeBavard(), "q", "a", "r")
        self.assertEqual(verdict, "a_verifier")

    def test_evaluation_et_rapport(self):
        questions = [
            {"id": "t1", "categorie": "Durée", "type": "dans_le_document",
             "question": "Combien de temps dure une rencontre fictive ?",
             "reponse_attendue": "Deux périodes de 30 minutes.", "loi_attendue": "7"},
            {"id": "t2", "categorie": "Hors", "type": "hors_document",
             "question": "Qui a gagné la coupe fictive ?", "reponse_attendue": "Refus", "loi_attendue": ""},
        ]
        modele = Modele("simule")
        assistant = Assistant(modele, self.index)
        sortie = evaluer(assistant, modele, questions, ["sans_contexte", "rag"],
                         self.dossier / "resultats_test.csv", afficher=lambda *_: None)
        with sortie.open(encoding="utf-8") as f:
            lignes = list(csv.DictReader(f))
        self.assertEqual(len(lignes), 4)
        rag = next(l for l in lignes if l["id"] == "t1" and l["mode"] == "rag")
        self.assertEqual(rag["recuperation_ok"], "1")
        self.assertEqual(rag["bonne_source"], "1")
        hors = next(l for l in lignes if l["id"] == "t2" and l["mode"] == "sans_contexte")
        self.assertEqual(hors["verdict_juge"], "correct")   # le modèle simulé refuse sans contexte
        texte = ecrire_rapport(sortie, self.dossier / "rapport.md", "simule")
        self.assertIn("| Indicateur | Sans document | Avec RAG |", texte)
        self.assertIn("Bonne loi parmi les passages retrouvés", texte)


class TestVersion2(unittest.TestCase):
    """Périmètre « 17 lois seulement », étiquettes, test de la recherche et comparaison."""

    @classmethod
    def setUpClass(cls):
        from tests.fixtures.creer_livret_ifab_fictif import generer as generer_livret
        cls.dossier = Path(tempfile.mkdtemp())
        cls.extraits = ingerer(generer_livret(cls.dossier / "livret.txt"), cls.dossier / "extraits.jsonl")

    def test_perimetre_17_lois(self):
        index = IndexBM25(self.extraits, exclure_hors_lois=True)
        self.assertTrue(index.extraits and all(e["loi"] != 0 for e in index.extraits))
        trouves = index.chercher("assistance vidéo normes de qualité", k=6)
        self.assertTrue(all(e["loi"] != 0 for e in trouves))

    def test_pas_de_loi_0_dans_les_etiquettes(self):
        from rag.assistant import formater_extraits
        hors = [e for e in self.extraits if e["loi"] == 0][:1] + [e for e in self.extraits if e["loi"] == 7][:1]
        texte = formater_extraits(hors)
        self.assertNotIn("[Loi 0]", texte)
        self.assertIn("[Hors des 17 lois]", texte)
        self.assertIn("[Loi 7]", texte)

    def test_tester_recherche(self):
        from rag.recherche import tester_recherche
        questions = [
            {"id": "t1", "type": "dans_le_document", "question": "Délai fictif de sortie du joueur remplacé", "loi_attendue": "3"},
            {"id": "t2", "type": "dans_le_document", "question": "Contenu fictif sur la rentrée de touche", "loi_attendue": "15"},
            {"id": "t3", "type": "hors_document", "question": "Salaire ?", "loi_attendue": ""},
        ]
        lignes, rates = tester_recherche(self.extraits, questions, ks=(4, 6))
        self.assertEqual(len(lignes), 4)          # en-tête, séparateur, 2 périmètres
        self.assertIn("/2", lignes[2])            # seules les 2 questions « dans le document » comptent
        self.assertEqual(set(rates), {(False, 4), (False, 6), (True, 4), (True, 6)})

    def test_versions_et_comparaison(self):
        from rag.rapport import comparer
        from rag.versions import VERSIONS
        questions = [{"id": "t1", "categorie": "x", "type": "dans_le_document",
                      "question": "Contenu fictif sur la durée du match", "reponse_attendue": "Deux périodes.",
                      "loi_attendue": "7"}]
        fichiers = {}
        for version, cfg in VERSIONS.items():
            modele = Modele("simule")
            index = IndexBM25(self.extraits, exclure_hors_lois=cfg["exclure_hors_lois"])
            assistant = Assistant(modele, index, k=cfg["k"], version=version)
            fichiers[version] = evaluer(assistant, modele, questions, ["sans_contexte", "rag"],
                                        self.dossier / f"resultats_{version}.csv", afficher=lambda *_: None)
            with fichiers[version].open(encoding="utf-8") as f:
                self.assertTrue(all(l["version"] == version for l in csv.DictReader(f)))
        texte = comparer([("Sans document", fichiers["v1"], "sans_contexte"), ("RAG v1", fichiers["v1"], "rag"),
                          ("RAG v2", fichiers["v2"], "rag")], self.dossier / "comparaison.md")
        self.assertIn("| Indicateur | Sans document | RAG v1 | RAG v2 |", texte)


class TestLivretIFAB(unittest.TestCase):
    """Mise en page réelle du livret 2026/27 (une page « Loi / N » par loi)."""

    @classmethod
    def setUpClass(cls):
        from tests.fixtures.creer_livret_ifab_fictif import generer as generer_livret
        dossier = Path(tempfile.mkdtemp())
        cls.extraits = ingerer(generer_livret(dossier / "livret.txt"), dossier / "extraits.jsonl")

    def test_les_17_lois_sans_alerte(self):
        _, alertes = controle_qualite(self.extraits)
        self.assertEqual(alertes, [])
        for n in range(1, 18):
            self.assertTrue(any(e["loi"] == n and "Contenu fictif" in e["texte"] for e in self.extraits), n)

    def test_preambule_var_et_qualite_hors_des_lois(self):
        for marque in ("Directives pour le", "assistance vidéo", "normes de qualité", "Table des matières"):
            concernes = [e for e in self.extraits if marque in e["texte"]]
            self.assertTrue(concernes, marque)
            self.assertTrue(all(e["loi"] == 0 for e in concernes), marque)

    def test_amendements_rattaches_a_leur_loi(self):
        amend = [e for e in self.extraits if "modifications 2026/27" in e["titre"]]
        self.assertEqual({e["loi"] for e in amend}, {3, 15})
        self.assertTrue(any("délai fictif" in e["texte"] and e["loi"] == 3 for e in amend))
        self.assertTrue(any("décompte fictif" in e["texte"] and e["loi"] == 15 for e in amend))
        var_amende = [e for e in self.extraits if "Texte amendé fictif" in e["texte"]]
        self.assertTrue(var_amende and all(e["loi"] == 0 for e in var_amende))


if __name__ == "__main__":
    unittest.main()

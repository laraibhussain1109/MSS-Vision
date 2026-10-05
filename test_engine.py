"""Unit tests for the chatbot engine. Run with:  python -m unittest -v"""
import json
import tempfile
import unittest
from pathlib import Path

from engine import LegalBot, tokenize

CASES = [
    ("I was fired without any notice", "wrongful_termination"),
    ("my landlord is keeping my deposit", "security_deposit"),
    ("How do I write a will?", "wills"),
    ("The police arrested my brother last night", "arrest_rights"),
    ("My employer hasn't paid my salary for two months", "unpaid_wages"),
    ("someone posted lies about me online", "defamation"),
    ("how do I register a trademark for my brand", "intellectual_property"),
    ("I want a divorce, where do I start?", "divorce"),
    ("The seller won't refund my defective phone", "consumer_rights"),
    ("my landlord sent me an eviction notice", "eviction"),
    ("Who gets custody of the kids?", "child_custody"),
    ("What happens if my father died with no will?", "probate"),
    ("How long do I have to file a lawsuit?", "statute_of_limitations"),
    ("debt collectors keep calling me", "debt_collection"),
    ("how much does a lawyer cost", "finding_lawyer"),
]


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bot = LegalBot(intake_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_knowledge_base_integrity(self):
        ids = {e["id"] for e in self.bot.entries}
        self.assertEqual(len(ids), len(self.bot.entries), "duplicate ids")
        for e in self.bot.entries:
            for key in ("title", "category", "keywords", "answer", "steps", "related"):
                self.assertTrue(e.get(key), f"{e['id']} missing {key}")
            for rel in e["related"]:
                self.assertIn(rel, ids)

    def test_retrieval_accuracy(self):
        for question, expected in CASES:
            with self.subTest(question=question):
                self.assertEqual(self.bot.respond(question).topic, expected)

    def test_next_steps_follow_up(self):
        self.bot.respond("I was fired without notice")
        reply = self.bot.respond("next steps")
        self.assertEqual(reply.topic, "wrongful_termination")
        self.assertIn("1.", reply.text)

    def test_next_steps_without_context(self):
        self.assertIsNone(self.bot.respond("next steps").topic)

    def test_urgent_notice(self):
        self.assertTrue(self.bot.respond("I was arrested yesterday").notice)
        self.assertFalse(self.bot.respond("how do I write a will").notice)

    def test_nonsense_falls_back(self):
        reply = self.bot.respond("qwerty zxcvb plugh")
        self.assertIsNone(reply.topic)
        self.assertIn("Browse topics", reply.suggestions)

    def test_chip_title_round_trip(self):
        reply = self.bot.respond("my landlord wants to evict me")
        for chip in reply.suggestions:
            if chip in ("Next steps", "Request a consultation"):
                continue
            self.assertIsNotNone(self.bot.respond(chip).topic, chip)

    def test_smalltalk_and_topics(self):
        self.assertIn("legal information assistant", self.bot.respond("hello").text)
        self.assertIn("Topics I can help with", self.bot.respond("topics").text)

    def test_intake_flow_saves_file(self):
        self.bot.respond("/intake")
        self.bot.respond("Jane Doe")
        self.bot.respond("housing")
        self.bot.respond("My landlord changed the locks.")
        bad = self.bot.respond("not-a-contact")
        self.assertIn("valid", bad.text)
        done = self.bot.respond("jane@example.com")
        self.assertIn("saved", done.text)
        files = list(Path(self.tmp.name).glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(json.loads(files[0].read_text())["name"], "Jane Doe")
        self.assertIsNone(self.bot.intake)

    def test_intake_cancel(self):
        self.bot.respond("book a consultation")
        self.assertIsNotNone(self.bot.intake)
        self.bot.respond("cancel")
        self.assertIsNone(self.bot.intake)

    def test_tokenizer_unifies_forms(self):
        self.assertEqual(tokenize("leases"), tokenize("lease"))
        self.assertEqual(tokenize("terminating"), tokenize("terminate"))


if __name__ == "__main__":
    unittest.main()

"""Conversation logic and retrieval engine for the legal consultancy chatbot.

Pure Python with no third-party dependencies, so it works fully offline.

How it works
------------
1. Every knowledge-base entry is turned into a weighted TF-IDF vector
   (title/keywords count more than the answer text).
2. A user message is matched by cosine similarity plus a small boost for
   exact keyword-phrase hits ("security deposit", "unfair dismissal", ...).
3. On top of retrieval sits a light dialogue layer: greetings, follow-ups
   ("next steps"), an urgent-situation notice, and a guided consultation
   intake that saves a request to disk.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


def _resource_dir() -> Path:
    """Folder holding bundled read-only files (works with PyInstaller too)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _data_dir() -> Path:
    """Writable folder for saved consultation requests."""
    if getattr(sys, "frozen", False):
        return Path.home() / "LegalChatbot"
    return Path(__file__).resolve().parent


# --------------------------------------------------------------------------- #
# Text processing
# --------------------------------------------------------------------------- #
STOPWORDS = frozenset(
    """a about after again all also am an and any are as at be because been before being
    both but by can could did do does doing down during each for from had has have having
    he her here him his how i if in into is it its just me more most my no nor not now of
    off on once only or other our out over own same she should so some such than that the
    their them then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your get got""".split()
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """A tiny suffix-stripping stemmer, good enough to unify common word forms."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith(("sses", "ches", "shes", "xes")):
        word = word[:-2]
    else:
        for suffix in ("ing", "ed"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        else:
            if word.endswith("s") and not word.endswith("ss"):
                word = word[:-1]
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    words = _WORD_RE.findall(text.lower().replace("'", ""))
    return [stem(w) for w in words if w not in STOPWORDS]


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
class Retriever:
    """TF-IDF cosine-similarity search over the knowledge base."""

    def __init__(self, entries: list[dict]):
        self.entries = entries
        docs: list[Counter] = []
        for e in entries:
            c: Counter = Counter()
            for t in tokenize(e["title"]):
                c[t] += 3
            for k in e["keywords"]:
                for t in tokenize(k):
                    c[t] += 3
            for q in e.get("questions", []):
                for t in tokenize(q):
                    c[t] += 2
            for t in tokenize(e["answer"]):
                c[t] += 1
            docs.append(c)

        n = len(docs)
        df: Counter = Counter()
        for c in docs:
            df.update(c.keys())
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vectors = [self._weigh(c) for c in docs]
        self.phrases = [
            [(re.compile(rf"\b{re.escape(k)}\b"), len(k.split())) for k in e["keywords"]]
            for e in entries
        ]

    def _weigh(self, counts: Counter) -> dict[str, float]:
        vec = {t: (1 + math.log(tf)) * self.idf.get(t, 0.0) for t, tf in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, text: str, top_k: int = 3) -> list[tuple[float, dict]]:
        query = Counter(t for t in tokenize(text) if t in self.idf)
        qvec = self._weigh(query) if query else {}
        lowered = text.lower()
        scored = []
        for i, vec in enumerate(self.vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in qvec.items())
            boost = sum(0.12 + 0.06 * (n - 1) for pat, n in self.phrases[i] if pat.search(lowered))
            score += min(boost, 0.4)
            if score > 0:
                scored.append((score, self.entries[i]))
        scored.sort(key=lambda s: s[0], reverse=True)
        return scored[:top_k]


# --------------------------------------------------------------------------- #
# Dialogue layer
# --------------------------------------------------------------------------- #
@dataclass
class Reply:
    text: str
    suggestions: list[str] = field(default_factory=list)
    notice: str = ""          # urgent notice shown before the main answer
    topic: str | None = None  # id of the knowledge-base entry used, if any


URGENT_RE = re.compile(
    r"\b(arrest(ed)?|detained|police|jail|summons|subpoena|served with|restraining order|"
    r"domestic violence|abus(e|ed|ive)|threat(en|ens|ened|ening)?)\b"
)
URGENT_NOTICE = (
    "**Urgent?** If you are in immediate danger, contact your local emergency services. "
    "If you have been arrested, charged, or served with court papers, speak to a licensed "
    "lawyer right away. Deadlines can be very short."
)

GREETING_RE = re.compile(r"^(hi|hello|hey|hiya|good (morning|afternoon|evening))( there| bot)?[\s!.]*$")
THANKS_RE = re.compile(r"^(thanks|thank you|thx|ty|cheers)\b")
BYE_RE = re.compile(r"^(bye|goodbye|see you|exit|quit)\b")
MORE_RE = re.compile(
    r"^(yes|yeah|sure|ok(ay)?|please)?[\s,]*(tell me )?"
    r"(more|next steps?|steps|what (should|can|do) i do( next)?|what now|how do i proceed)\b"
)
TOPICS_RE = re.compile(r"^(/topics|topics|browse topics|what can you (do|help with)|list topics)\b")
HELP_RE = re.compile(r"^(/help|help)\b")
INTAKE_RE = re.compile(
    r"^(/intake|request a consultation|book a consultation)|"
    r"\b(book|schedule|arrange|request)\b.*\b(consultation|appointment|lawyer|attorney)\b|"
    r"\b(speak|talk) to (a |an )?(real )?(lawyer|attorney|human|advisor|adviser)\b"
)
FOLLOWUP_CUE_RE = re.compile(r"\b(it|that|this|they|them|those|also|what about|and if|what if|how long)\b")

INTAKE_STEPS = [
    ("name", "Let's set up a consultation request. What is your full name?"),
    ("area", "Which area does your matter fall under? (for example employment, housing, family, contracts)"),
    ("summary", "Please describe your situation in a few sentences. Avoid sharing passwords or ID numbers."),
    ("contact", "Finally, how can we reach you? (email address or phone number)"),
]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DISCLAIMER_FOOTER = "_General information only, not legal advice._"


def _valid_contact(text: str) -> bool:
    text = text.strip()
    return bool(EMAIL_RE.match(text)) or sum(c.isdigit() for c in text) >= 7


class LegalBot:
    CONFIDENT = 0.22   # score needed to answer directly
    TENTATIVE = 0.10   # score needed to offer "did you mean" suggestions

    def __init__(self, kb_path: Path | str | None = None, intake_dir: Path | str | None = None):
        kb_path = Path(kb_path) if kb_path else _resource_dir() / "knowledge_base.json"
        with open(kb_path, encoding="utf-8") as fh:
            self.entries: list[dict] = json.load(fh)
        self.by_id = {e["id"]: e for e in self.entries}
        self.by_title = {e["title"].lower(): e for e in self.entries}
        self.retriever = Retriever(self.entries)
        self.intake_dir = Path(intake_dir) if intake_dir else _data_dir() / "consultation_requests"
        self.last_entry: dict | None = None
        self.intake: dict | None = None

    # ---- public API -------------------------------------------------------
    def reset(self) -> None:
        self.last_entry = None
        self.intake = None

    def greeting(self) -> Reply:
        return Reply(
            "Hello, I'm your **legal information assistant**. Describe your situation in plain "
            "language, for example _\"my landlord won't return my deposit\"_, and I'll explain the "
            "basics and practical next steps.\n\nType **topics** to see what I cover, or "
            "**/intake** to request a consultation with a lawyer.",
            suggestions=["Browse topics", "I was fired from my job", "Request a consultation"],
        )

    def respond(self, message: str) -> Reply:
        text = message.strip()
        if not text:
            return Reply("Please type your question and I'll do my best to help.")
        if self.intake is not None:
            return self._handle_intake(text)

        low = text.lower()
        notice = URGENT_NOTICE if URGENT_RE.search(low) else ""

        if GREETING_RE.match(low):
            return self.greeting()
        if THANKS_RE.match(low):
            return Reply("You're welcome. Ask me anything else, or type **topics** to browse.")
        if BYE_RE.match(low):
            return Reply("Take care. Remember that a licensed lawyer can advise on your specific case.")
        if HELP_RE.match(low):
            return self._help()
        if TOPICS_RE.match(low):
            return self._topics()
        if INTAKE_RE.search(low):
            return self._start_intake()
        if low in self.by_title:                      # user clicked a suggestion chip
            return self._answer_entry(self.by_title[low], notice)
        if MORE_RE.match(low):
            return self._next_steps(notice)

        reply = self._search(text, low)
        reply.notice = notice
        return reply

    # ---- internals --------------------------------------------------------
    def _search(self, text: str, low: str) -> Reply:
        hits = self.retriever.search(text)
        best = hits[0][0] if hits else 0.0

        # Short follow-up such as "what about my deposit?" or "how long do I have?"
        if best < self.CONFIDENT and self.last_entry and len(text.split()) <= 10 \
                and FOLLOWUP_CUE_RE.search(low):
            context = text + " " + " ".join(self.last_entry["keywords"][:4])
            ctx_hits = self.retriever.search(context)
            if ctx_hits and ctx_hits[0][0] >= self.CONFIDENT:
                hits, best = ctx_hits, ctx_hits[0][0]

        if best >= self.CONFIDENT:
            return self._answer_entry(hits[0][1])
        if best >= self.TENTATIVE:
            titles = [e["title"] for _, e in hits]
            return Reply("I'm not completely sure I understood. Did you mean one of these?",
                         suggestions=titles)
        return Reply(
            "I don't have specific guidance on that yet. Try rephrasing with a few key words "
            "(for example _eviction_, _unpaid wages_, _divorce_), browse the topics I cover, or "
            "request a consultation with a lawyer.",
            suggestions=["Browse topics", "Request a consultation"],
        )

    def _answer_entry(self, entry: dict, notice: str = "") -> Reply:
        self.last_entry = entry
        text = (f"**{entry['title']}**\n\n{entry['answer']}\n\n"
                f"Type **next steps** for practical steps.\n{DISCLAIMER_FOOTER}")
        related = [self.by_id[r]["title"] for r in entry.get("related", [])[:2]]
        return Reply(text, suggestions=["Next steps", *related, "Request a consultation"],
                     notice=notice, topic=entry["id"])

    def _next_steps(self, notice: str) -> Reply:
        if not self.last_entry:
            return Reply("Tell me about your situation first, then I can suggest practical next steps.",
                         suggestions=["Browse topics"])
        e = self.last_entry
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(e["steps"], 1))
        related = [self.by_id[r]["title"] for r in e.get("related", [])[:3]]
        return Reply(f"**Practical next steps: {e['title']}**\n\n{steps}\n\n{DISCLAIMER_FOOTER}",
                     suggestions=[*related, "Request a consultation"], notice=notice, topic=e["id"])

    def _topics(self) -> Reply:
        groups: dict[str, list[str]] = {}
        for e in self.entries:
            groups.setdefault(e["category"], []).append(e["title"])
        lines = [f"**{cat}:** " + "; ".join(titles) for cat, titles in sorted(groups.items())]
        return Reply("**Topics I can help with**\n\n" + "\n".join(lines) +
                     "\n\nType a topic or just describe your situation.")

    def _help(self) -> Reply:
        return Reply(
            "**How to use this assistant**\n\n"
            "• Describe your situation in plain language.\n"
            "• Type **next steps** after an answer for a practical checklist.\n"
            "• Type **topics** to see everything I cover.\n"
            "• Type **/intake** to request a consultation with a lawyer.\n\n"
            "I provide general legal information, not legal advice. Laws differ by country and "
            "state, so always confirm details with a licensed lawyer where you live."
        )

    # ---- consultation intake ---------------------------------------------
    def _start_intake(self) -> Reply:
        self.intake = {"step": 0, "data": {}}
        return Reply(INTAKE_STEPS[0][1] + "\n\n_Type **cancel** at any time to stop._")

    def _handle_intake(self, text: str) -> Reply:
        if text.lower() in {"cancel", "/cancel", "stop"}:
            self.intake = None
            return Reply("No problem, I've cancelled the consultation request. "
                         "You can restart any time with **/intake**.")
        key = INTAKE_STEPS[self.intake["step"]][0]
        if key == "name" and len(text) < 2:
            return Reply("Please enter your full name.")
        if key == "contact" and not _valid_contact(text):
            return Reply("That doesn't look like a valid email or phone number. Please try again, "
                         "or type **cancel** to stop.")
        self.intake["data"][key] = text
        self.intake["step"] += 1
        if self.intake["step"] < len(INTAKE_STEPS):
            nxt = INTAKE_STEPS[self.intake["step"]]
            chips = ["Employment", "Housing", "Family", "Contracts"] if nxt[0] == "area" else []
            return Reply(nxt[1], suggestions=chips)
        return self._finish_intake()

    def _finish_intake(self) -> Reply:
        data = self.intake["data"]
        now = datetime.now()
        ref = now.strftime("LC-%Y%m%d-%H%M%S")
        record = {"reference": ref, "created": now.isoformat(timespec="seconds"), **data}
        self.intake = None
        try:
            self.intake_dir.mkdir(parents=True, exist_ok=True)
            with open(self.intake_dir / f"{ref}.json", "w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            return Reply(f"I couldn't save your request ({exc}). Please copy your details and "
                         "contact the office directly.")
        return Reply(
            f"**Consultation request saved.** Reference: **{ref}**\n\n"
            f"Name: {data['name']}\nArea: {data['area']}\nContact: {data['contact']}\n\n"
            "A member of the team can use this summary to follow up with you. Submitting this "
            "request does not create a lawyer-client relationship.",
            suggestions=["Browse topics"],
        )

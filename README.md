# Legal Information Assistant

This is a small, offline college project that demonstrates document retrieval and a
desktop chat interface. It matches a user's words against a hand-maintained JSON
knowledge base; it does **not** call a generative-AI service, invent case citations, or
replace a lawyer.

## Run the project

Python 3.10 or newer is recommended.

```bash
python -m pip install -r requirements.txt
python gui.py
```

Run the engine tests without installing the graphical dependency:

```bash
python -m unittest -v
```

## What it does

- retrieves an educational summary from 27 common legal topics;
- keeps short conversational context for follow-up questions;
- highlights messages that may involve immediate danger or urgent deadlines;
- offers practical checklists and related topics;
- collects a consultation request only after explicit permission; and
- exports a plain-text transcript when the user chooses to do so.

## Legal and privacy limitations

The answers are general educational summaries. Laws vary by jurisdiction, change over
time, and depend on facts that this demonstration cannot verify. Before real-world use,
a qualified lawyer should review every knowledge-base entry for the intended
jurisdiction and add links to current primary legal sources. The app must never be
presented as a lawyer, used to predict a case result, or relied on for a deadline.

The program runs locally. Ordinary conversations remain in memory unless the user
exports them. Consultation intake is different: after showing a clear notice and
receiving `I consent`, it writes the supplied name, jurisdiction, issue summary and
contact detail to `consultation_requests/`. Files are created with owner-only
permissions where the operating system supports them. There is no automatic delivery
to a law firm. Users should avoid entering government identifiers, passwords, banking
details, or privileged documents. A real deployment needs a retention/deletion policy,
encryption, access controls, breach procedures, and jurisdiction-specific consent text.

## Academic integrity and content provenance

The application is a compact implementation maintained in this repository with
Python's standard library and PyQt6. The retrieval method is the standard TF-IDF and
cosine-similarity technique; those general algorithms are not presented as novel
research. The knowledge base intentionally contains no quotations or fabricated case
citations. This README does not certify originality: each submitter remains responsible
for checking the work, documenting sources, and following their institution's policy.

Automated “AI/plagiarism detector” scores are not reliable evidence of authorship.
Instead of trying to manipulate such a score, submitters should disclose assistance in
the form required by their college, retain their commit history, cite any future source
material beside the relevant knowledge-base entry, and be prepared to explain the code.

## Project structure

- `engine.py` — tokenisation, TF-IDF retrieval, conversation flow, and consent-based intake.
- `gui.py` — PyQt6 desktop interface and transcript export.
- `knowledge_base.json` — searchable educational summaries and checklists.
- `test_engine.py` — retrieval, safety notice, dialogue, and privacy tests.

## Extending safely

1. Choose one supported jurisdiction instead of silently mixing legal systems.
2. Have a subject-matter expert review additions and record the review date.
3. Link to legislation, court rules, or official government guidance in the entry.
4. Add retrieval tests for both correct matches and potentially dangerous mismatches.
5. Keep the fallback honest: when confidence is low, route the user to qualified help.

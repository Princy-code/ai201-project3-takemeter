# TakeMeter — A Discourse-Quality Classifier for Hacker News

TakeMeter is a fine-tuned text classifier that labels Hacker News comments as `analysis`,
`hot_take`, or `reaction`. This project compares a fine-tuned **DistilBERT** model against a
zero-shot **Groq `llama-3.3-70b-versatile`** baseline on the same held-out test set, and honestly
reports where the model works and where it falls apart.

The short version: the zero-shot baseline beat the fine-tuned model, and the fine-tuned model
collapsed to a single class. That negative result, and the analysis of *why*, is the core finding
of this project.

---

## Community

**Hacker News** comment sections. HN discussion is text-heavy and varies enormously in quality —
the same thread often contains a rigorous technical argument, a confident one-line opinion with no
support, and a pure emotional reaction. That spread is what makes it a good classification target,
and the distinction between a reasoned argument and a bare assertion is something HN regulars
already track ("source?" / "this is just an assertion" are common replies).

> **Data-source note:** The project was originally planned for r/LocalLLaMA, but Reddit's API now
> requires app registration I couldn't complete, and unauthenticated requests returned HTTP 403. I
> pivoted to Hacker News via its free, no-auth Algolia API. The `analysis / hot_take / reaction`
> taxonomy transferred directly. (See the Spec Reflection and AI Usage sections.)

---

## Label Taxonomy

Three mutually exclusive labels — each comment gets exactly one.

| Label | Definition | Example |
|---|---|---|
| `analysis` | A structured argument backed by specific, verifiable evidence (numbers, a mechanism, technical reasoning). The point would stand even with the opinion framing removed. | *"4 engines are twice as likely to have a major failure than 2 … there are many cases of single-engine failure bringing down the airplane."* |
| `hot_take` | A bold, confident opinion stated **without** real evidence. The claim might be true, but it asserts rather than argues. | *"Today's airliners cruise slower than a 747."* |
| `reaction` | An immediate emotional or anecdotal response to something — a launch, a headline, a personal story — with little to no argument. | *"I got what was probably my last 747 trip a few years ago … I'm really glad I was able to do it."* |

**Why these work:** each decision boundary fits in one sentence, two readers applying the
definitions agree on most comments, and the distinctions reflect how the community actually talks
about comment quality.

---

## Dataset

- **Source:** 347 public Hacker News comments collected via the Algolia API (`search_by_date`,
  `tags=comment`), mixing topical queries (AI, LLM, Rust, startup, etc.) with general recent
  comments. HTML and URLs stripped; filtered to 5–200 words to drop one-liners and walls of text.
- **Split:** the notebook splits 70 / 15 / 15 into train (242) / validation (52) / test (53),
  stratified by label.
- **Labeling process:** Groq `llama-3.3-70b-versatile` pre-labeled all 347 comments; I then
  reviewed every row and **corrected 84 of them** by hand. The `suggested` column in the dataset
  preserves Groq's original guess alongside my final `label` for transparency.

**Label distribution (full dataset):**

| Label | Count | Share |
|---|---|---|
| `analysis` | 181 | 52.2% |
| `reaction` | 92 | 26.5% |
| `hot_take` | 74 | 21.3% |
| **Total** | **347** | **100%** |

Every class clears the 20% floor, but `analysis` is the majority at 52%. **This imbalance turns
out to be the central character in the results below.**

### Three genuinely difficult examples

1. **Evidence-flavored hot take.** *"The public will get ~5.5 level models. Private industry will
   essentially get ITAR access… Its totally sensible that the US will keep strong AI to itself."*
   It name-drops a real mechanism (ITAR) but uses it to decorate a confident prediction rather
   than to argue. **Decision:** `hot_take` — the evidence is ornamental, not load-bearing.
2. **Anecdote with a lesson.** *"I was taught cursive in 2nd grade and my handwriting is
   gobsmackingly horrible… I'm so happy computers made handwritten exams obsolete."* A personal
   story that gestures at a general point. **Decision:** `reaction` — it's primarily "here's what
   happened to me," with no generalizable argument.
3. **Hedged opinion.** *"While being slow to pass judgment is valuable, I think 3 years is plenty
   of time to wait for proof of concept… it's not panning out."* Reads analytical but offers no
   verifiable evidence — just a confident timeline judgment. **Decision:** `hot_take`.

These three were also the kind of case the model got wrong (see Failure Analysis).

---

## Fine-Tuning Approach

- **Base model:** `distilbert-base-uncased` (HuggingFace), a 66M-parameter distilled BERT.
- **Training:** Google Colab T4 GPU, via the HuggingFace `Trainer`.
- **Hyperparameters:** the notebook defaults — **3 epochs, learning rate 2e-5, batch size 16.**
- **Key hyperparameter decision:** I kept the defaults rather than tuning. Given only 242 training
  examples, more epochs risked overfitting and a larger learning rate risked instability; 3 epochs
  at 2e-5 is a conservative, standard starting point. In hindsight (see Reflection), the more
  consequential decision I *didn't* make was handling class imbalance — and that's what sank the
  model.

---

## Baseline Comparison

The zero-shot baseline is Groq `llama-3.3-70b-versatile`, prompted with the same label definitions
and instructed to output only a single label word. It received **no task-specific training** and
was evaluated on the identical 53-example test set.

---

## Evaluation Report

### Headline numbers

| Metric | Baseline (Groq zero-shot) | Fine-tuned (DistilBERT) |
|---|---|---|
| **Accuracy** | **0.660** | 0.528 |
| **Macro-F1** | **0.60** | 0.23 |
| Weighted F1 | 0.66 | 0.37 |

**The fine-tuned model performed worse than the baseline by every measure** (–13.2 points of
accuracy, –0.37 macro-F1). The negative `improvement` is the result, not a bug.

### Per-class metrics

**Baseline (Groq zero-shot):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `analysis` | 1.00 | 0.64 | 0.78 | 28 |
| `hot_take` | 0.75 | 0.27 | 0.40 | 11 |
| `reaction` | 0.45 | 1.00 | 0.62 | 14 |

**Fine-tuned (DistilBERT):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `analysis` | 0.53 | 1.00 | 0.69 | 28 |
| `hot_take` | 0.00 | 0.00 | 0.00 | 11 |
| `reaction` | 0.00 | 0.00 | 0.00 | 14 |

### Confusion matrices (rows = true, cols = predicted)

**Baseline:**

| true \ pred | analysis | hot_take | reaction |
|---|---|---|---|
| **analysis** | 18 | 1 | 9 |
| **hot_take** | 0 | 3 | 8 |
| **reaction** | 0 | 0 | 14 |

**Fine-tuned:**

| true \ pred | analysis | hot_take | reaction |
|---|---|---|---|
| **analysis** | 28 | 0 | 0 |
| **hot_take** | 11 | 0 | 0 |
| **reaction** | 14 | 0 | 0 |

(A rendered version is committed as `confusion_matrix.png`.)

### What the matrices reveal

**The fine-tuned model collapsed to the majority class.** It predicted `analysis` for all 53 test
examples and never once predicted `hot_take` or `reaction`. Its 52.8% accuracy is *exactly* the
share of `analysis` in the test set — i.e., it learned the single rule "always say analysis,"
which is no better than a constant predictor. Its perfect `analysis` recall (1.00) is meaningless
because it comes at the cost of zero recall on everything else.

**The baseline has a real, directional error pattern.** Look at the lower-left of the baseline
matrix: it is all zeros. Groq *never* misclassifies a `hot_take` or `reaction` as `analysis` —
it's strict about what counts as a reasoned argument (precision 1.00 on `analysis`). Instead it
**over-predicts `reaction`** (recall 1.00, precision 0.45), dumping 9 true `analysis` and 8 true
`hot_take` comments into it, and it **under-detects `hot_take`** (recall 0.27 — it catches only 3
of 11). In plain terms: when the baseline is unsure, it defaults to "reaction," and it struggles
most with the `hot_take` vs everything-else boundary — the hardest, most subjective distinction in
the taxonomy.

### Failure analysis — 3 specific wrong predictions (fine-tuned model)

Because the model predicted `analysis` for everything, every non-`analysis` test comment is a
failure. Three representative ones:

1. **TRUE `hot_take` → PRED `analysis`:** *"…3 years is plenty of time to wait for proof of concept
   to pan out. It's not panning out…"* — A confident judgment with no evidence. The model saw
   technical vocabulary ("proof of concept," "senior Eng") and defaulted to `analysis`. **Why it
   failed:** with only ~52 `hot_take` examples in training and a strong majority-class prior, the
   model never learned that *tone of confidence ≠ presence of evidence.*
2. **TRUE `reaction` → PRED `analysis`:** *"i was taught cursive in 2nd grade and my handwriting is
   gobsmackingly horrible… so happy computers made handwritten exams obsolete."* — A personal
   anecdote. **Why it failed:** the model has no representation of "anecdote vs argument"; it
   simply defaulted to the majority label.
3. **TRUE `hot_take` → PRED `analysis`:** *"The public will get ~5.5 level models. Private industry
   will get ITAR access… totally sensible that the US will keep strong AI to itself."* — The
   ITAR reference is decorative, not evidentiary. **Why it failed:** surface technical content
   pulled the prediction toward `analysis`, the exact trap the taxonomy's edge-case rule was
   written to handle — but the model never learned that rule from so few counter-examples.

The common thread is not three separate mistakes — it is **one systematic failure**: class
collapse driven by a 52% majority class and a tiny training set, with the model exploiting "always
predict `analysis`" as the lowest-loss shortcut.

### Reflection — what the model learned vs. what I intended

I intended the model to learn the *distinction* between reasoned argument, bare assertion, and
emotional reaction. What it actually learned was the **base rate of the training labels** — "most
comments are `analysis`, so guess `analysis`." It captured the class prior, not the concept.

This is the gap the assignment points at: the fine-tuned model's decision boundary isn't a
boundary at all; it's a constant. The zero-shot LLM, by contrast, never saw my data but *did*
encode a usable notion of "is this an argument or a reaction," which is why it scored higher
despite zero training. The lesson: for a small, imbalanced, subjective dataset, a well-prompted
large model can beat fine-tuning outright, and fine-tuning needs class-imbalance handling
(weighted loss, oversampling the minority classes, or more data) before it can learn anything but
the majority label. If I extended this project, my first move would be class-weighted loss or
balancing the training set to ~equal counts, then re-running — I'd expect the collapse to break.

### Sample classifications (fine-tuned model)

| Comment (truncated) | Predicted | True |
|---|---|---|
| "It is the result of two decades of research in image reconstruction algorithms. The ML is part of it, but selling it as 'AI' is marketing." | `analysis` | `analysis` ✓ |
| "Today's airliners cruise slower than a 747." | `analysis` | `hot_take` ✗ |
| "Hopefully I get a MacBook Pro soon enough to run some small LLMs." | `analysis` | `reaction` ✗ |
| "4 engines are twice as likely to have a major failure than 2…" | `analysis` | `analysis` ✓ |
| "I don't know, middle management is all about people and project management…" | `analysis` | `hot_take` ✗ |

The one correctly-predicted `analysis` example is reasonable: it makes a concrete claim about
image-reconstruction research and distinguishes the technique from its marketing — genuinely a
reasoned argument. But the model gets it "right" for the wrong reason: it predicts `analysis` for
*everything*, so its correct calls carry no real signal.

---

## Spec Reflection

- **One way the spec guided implementation:** the spec's insistence on a zero-shot baseline *before*
  fine-tuning is what made this project interpretable. Without the 66% baseline as a reference,
  the fine-tuned 52.8% would look like a mediocre-but-okay number; against the baseline it's
  clearly a regression, which forced the real diagnosis (class collapse).
- **One way implementation diverged, and why:** the data source changed from r/LocalLLaMA to Hacker
  News after Reddit's API blocked collection. The taxonomy and pipeline were unaffected, but the
  domain shifted from local-LLM discussion to general HN tech discourse.

---

## AI Usage

1. **Annotation assistance.** I used Groq `llama-3.3-70b-versatile` (via a `prelabel.py` script I
   wrote) to pre-label all 347 comments. I then reviewed every row against my label definitions
   and **overrode 84 of Groq's labels** — mostly `hot_take → analysis` where it under-credited
   evidence-backed arguments, and `analysis → reaction` where it mistook personal anecdotes for
   argument. The dataset's `suggested` column preserves Groq's original guesses for comparison.
2. **Failure-pattern surfacing.** After evaluation I used an LLM to help articulate the
   majority-class-collapse pattern from the confusion matrix, then verified it directly against the
   matrix (`[[28,0,0],[11,0,0],[14,0,0]]`) and the per-class F1 scores before writing it up — the
   numbers, not the model, are the source of every claim in the report.

No AI wrote the final labels (I did), and no AI numbers were used in the evaluation — all metrics
come from the notebook's `scikit-learn` output.

---

## Repository Contents

| File | What it is |
|---|---|
| `planning.md` | Design thinking: community, labels, edge cases, metrics, success criteria, AI plan |
| `takemeter_dataset.csv` | 347 labeled comments (`text`, `label`, `notes`) |
| `evaluation_results.json` | Accuracy numbers exported from the notebook |
| `confusion_matrix.png` | Rendered confusion matrix for the fine-tuned model |
| `README.md` | This file |

## How to Reproduce

1. Open the TakeMeter starter notebook in Google Colab; set runtime to T4 GPU.
2. Add a Groq API key (Colab Secrets, `GROQ_API_KEY`).
3. Run Section 1 and upload `takemeter_dataset.csv`; set the label map to
   `analysis / hot_take / reaction`.
4. Run Sections 2–6 in order (split → fine-tune → evaluate → baseline → comparison/export).
5. Outputs `evaluation_results.json` and `confusion_matrix.png`.

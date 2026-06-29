# TakeMeter — Planning

A fine-tuned text classifier that evaluates discourse quality in **Hacker News** comments,
labeling each as `analysis`, `hot_take`, or `reaction`.

---

## 1. Community

**Chosen community:** Hacker News (news.ycombinator.com) comment sections.

**Why this community:** HN discussion is active, text-heavy, and varies enormously in quality.
The same thread routinely contains rigorous technical arguments, confident one-line opinions
with no support, and pure emotional reactions to a launch or headline. That spread is exactly
what makes it a good classification target.

**Why it's a good fit for classification:** The distinction between *a reasoned argument*,
*a bald assertion*, and *an emotional reaction* is something HN regulars implicitly track —
"source?" and "this is just an assertion" are common replies. The boundary matters to
participants, which is the test for a meaningful taxonomy.

> **Note on the data source:** I originally planned to collect from r/LocalLLaMA, but Reddit's
> API now requires app registration that I couldn't complete in time, and unauthenticated
> access returned HTTP 403. I pivoted to Hacker News, whose Algolia API
> (hn.algolia.com/api/v1) is free and requires no authentication. The analysis / hot_take /
> reaction taxonomy transferred cleanly. This pivot is documented in the README's process notes.

---

## 2. Labels

Three mutually exclusive labels. Each comment gets exactly one.

### `analysis`
A structured argument backed by specific, verifiable evidence — numbers, a described mechanism,
technical reasoning, or a concrete comparison. If you removed the opinion framing, the evidence
would still support the point.
- Example: "4 engines are twice as likely to have a major failure than 2 ... there are many cases
  of single-engine failure bringing down the airplane." (reasoned probability argument)
- Example: a comment walking through how ACA subsidy cliffs interact with capital-loss deduction
  limits, citing the $3,000 cap.

### `hot_take`
A bold, confident opinion stated **without** real evidence. The claim might be true, but the
comment *asserts* rather than *argues*.
- Example: "Today's airliners cruise slower than a 747." (bare assertion)
- Example: "AI bad / AI sucks / AI can't replace me -- load of [cope]."

### `reaction`
An immediate emotional or anecdotal response to something — a launch, a headline, a personal
story — with little to no argument.
- Example: "I got what was probably my last 747 trip a few years ago ... I'm really glad I was
  able to do it."
- Example: "Hopefully I get a MacBook Pro soon enough to run some small LLMs."

**Why these work:** (1) each decision boundary fits in one sentence, (2) two readers applying the
definitions agree on most comments, and (3) the distinctions reflect how HN actually talks about
comment quality.

---

## 3. Hard Edge Cases

### Edge case A — the evidence-flavored hot take (`analysis` vs `hot_take`)
A comment that gestures at one fact or number to prop up a much larger claim.

**Decision rule:** If the comment gives specific, verifiable evidence that would support the claim
*even with the opinion stripped out* -> `analysis`. If the fact is decorative or cherry-picked --
there to sound credible, not to actually reason -- -> `hot_take`.

### Edge case B — anecdote vs argument (`reaction` vs `analysis`)
A personal story that contains a general lesson.

**Decision rule:** If the comment generalizes from the story into a verifiable claim or mechanism
-> `analysis`. If it's primarily "here's what happened to me" with no general argument ->
`reaction`. (This was the most common correction I made: Groq's pre-labeling tended to over-call
personal stories as `analysis`.)

---

## 4. Data Collection Plan

- **Source:** public Hacker News comments via the Algolia search API (search_by_date,
  tags=comment). Public content only, no authentication.
- **Method:** a Python script (hn_collect.py) queried a mix of topical terms (AI, LLM, Rust,
  startup, etc.) plus general recent comments, stripped HTML/URLs, and filtered to 5-200 words to
  drop one-liners and walls of text. Collected 347 comments.
- **Balance goal:** >=20% per label, none above ~70%.
- **Result after labeling:** analysis 181 / reaction 92 / hot_take 74 -- all classes well above
  the floor.

---

## 5. Evaluation Metrics

- **Macro-F1 (primary):** unweighted mean of per-class F1. Classes are imbalanced (analysis is the
  majority) and all three matter equally, so macro-F1 is the headline number.
- **Per-class precision / recall / F1:** to see which distinction the model learns and which it
  doesn't.
- **Confusion matrix:** to read the direction of errors (e.g., predicting `hot_take` when the
  truth is `analysis`).

**Why accuracy alone isn't enough:** since `analysis` is ~52% of the data, a model that just
predicts `analysis` would score ~52% accuracy while completely failing the other two classes.
Macro-F1 and per-class metrics expose that; accuracy hides it.

---

## 6. Definition of Success

- **Beats the baseline** (zero-shot Groq llama-3.3-70b-versatile) on macro-F1.
- **Macro-F1 >= 0.65** on the held-out test set (a realistic bar for a 3-way subjective task on
  ~350 examples).
- **No class with F1 < 0.50** -- the model shouldn't be blind to any one label.
- **Good enough for a real tool:** if it could flag likely low-evidence `hot_take` comments for a
  human moderator to glance at, it's useful even if imperfect.
- **Red flag:** >0.95 accuracy on this subjective task would signal leakage or labels too easy.

---

## 7. AI Tool Plan

- **Annotation assistance (used):** Groq llama-3.3-70b-versatile pre-labeled all 347 comments via
  prelabel.py. I then reviewed every row and corrected 84 of them (mostly hot_take -> analysis,
  where Groq under-credited evidence-backed arguments; and analysis -> reaction for personal
  anecdotes). The `suggested` column preserves Groq's original guess for disclosure.
- **Baseline (required):** the same Groq model is the zero-shot baseline, run on the locked test
  set with no task-specific training.
- **Failure analysis (planned):** after evaluation, paste misclassified test examples to an LLM,
  ask it to surface patterns (e.g., a confused label pair, short comments), then verify each
  pattern by re-reading before writing it up.

---

## 8. Spec Reflection

- **One way the spec guided implementation:** the spec's requirement to run a zero-shot baseline
  *before* fine-tuning is what made the result interpretable. Without the 66% baseline as a
  reference point, the fine-tuned model's 51% accuracy would read as "mediocre but okay"; against
  the baseline it's clearly a regression, which forced the real diagnosis (the model never learned
  the `hot_take` class).
- **One way implementation diverged from the spec and why:** the data source changed from
  r/LocalLLaMA to Hacker News after Reddit's API required app registration I couldn't complete in
  time and returned HTTP 403 for unauthenticated access. The taxonomy and pipeline were unaffected;
  only the domain shifted.

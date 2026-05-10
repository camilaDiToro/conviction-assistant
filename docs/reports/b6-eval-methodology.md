# B6 — eval methodology

**Companion to:** `docs/reports/b6-eval-results.md` (numbers) and `docs/reports/b6-improvement-proposals.md` (alternatives, including the planned hybrid upgrade).

Every count in this document was re-verified against the live parser and the fixture YAML on 2026-05-10. Where older docs (CLAUDE.md, ROADMAP B2) disagree, this document is correct.

---

## The corpus the fixture is built against

Verified by running the parser:

| Statistic                       | Value                                          |
|---------------------------------|------------------------------------------------|
| Markdown documents              | 30                                             |
| Total passages (one per `##`)   | 423                                            |
| Passage length (chars), p10/median/p90 | 750 / 1,536 / 3,507                     |

Document language mix: 13 PT-body, 7 EN-body, 10 mixed (typically EN headings on a PT body, or vice versa). Mixed-heading docs are the cross-language risk surface for BM25.

## How the test cases were built

`tests/fixtures/retrieval_golden.yaml` was authored manually in commit `b41476d`:

1. **Read each conviction document end-to-end** — no LLM-generated query bank.
2. **Write each query *after* reading the cited passage(s)** so the answer is genuinely present, not just plausibly findable.
3. **Verify each `passage_id` against parser output** — slug-based IDs would silently rot if not re-checked.
4. **Tag each case with a `bucket`** classifying *why* it would be hard or easy for BM25 (literal / topic / cross_lang).
5. **Add free-text `notes:`** flagging known BM25 risks — these are evaluator hints, not assertions.

**Verification on 2026-05-10:** the fixture references **38 distinct `passage_id`s**; all 38 exist in parser output. Zero invented IDs. Spot-checks of representative slugs confirm correct NFKD-strip-accents → lowercase → dash-join.

## Fixture composition

| Dimension                                | Count |
|------------------------------------------|-------|
| Total cases                              | 29    |
| `bucket: literal`                        | 16    |
| `bucket: topic`                          | 8     |
| `bucket: cross_lang`                     | 5     |
| `language: pt` (PT query)                | 17    |
| `language: en` (EN query)                | 8     |
| `language: es` (ES query)                | 4     |
| Cases with **1** `expected_passage_ids`  | 19    |
| Cases with **2** `expected_passage_ids`  | 10    |

**Bucket definitions** (from the YAML preamble):

| Bucket       | Definition |
|--------------|------------|
| `literal`    | Query mentions an exact term from the heading or body. |
| `topic`      | Query asks the concept by paraphrase / synonym — no shared content words with the heading. |
| `cross_lang` | Query language ≠ passage language. Designed to fail under BM25 (canary for the hybrid upgrade). |

**`expected_passage_ids` shape:** the *first* id is the **primary** expected hit; additional ids are **secondary signal** — another passage that genuinely answers part of the same question. 4 of the 5 cross_lang cases are ES-against-PT-or-EN; 1 (`family-office-sucessao-cross-lang`) is PT-against-EN.

## How a case is tested

```python
hits = await search_convictions(query, k=5)
ids_returned = [h.passage_id for h in hits]
```

- `k = 5` (pinned in the fixture preamble, the ROADMAP B6 step, and the tool's Python default).
- Top-5 hits are inspected for `passage_id` membership — ranks within the top-5 do not affect scoring.
- The fixture is loaded once per pytest invocation (module-scoped fixture) and the corpus is ingested once.

## How scores are calculated

The test computes **two scores per case**, then aggregates per bucket and overall:

### Score 1 — primary-only (the gate)

```
score_primary(case) = 1 if case.expected_passage_ids[0] in ids_returned else 0
```

This is the strict "did the system retrieve the *intended* passage?" question. Each bucket has a floor:

- `literal` ≥ 90% (currently 93.8%)
- `topic` ≥ 50% (currently 62.5%)
- `cross_lang` reported only — not asserted (currently 0%)

If any gated bucket falls below its floor, the test fails. Cross-language failures are surfaced by the breakdown but don't gate, because the ROADMAP says cross_lang must not auto-promote to hybrid — the failures are the trigger for a conversation, not for a gate.

### Score 2 — primary + weighted secondary (printed alongside)

```
score_weighted(case) = 1.0  if primary in ids_returned
                       0.5  elif any(sec in ids_returned for sec in case.expected_passage_ids[1:])
                       0.0  otherwise
```

The 0.5 weight encodes "you found a legitimate but secondary passage" — useful for cases like `cripto-tributacao-cross-doc` whose own notes call both ids "legitimate primary candidates". At the current BM25 baseline, no failing case's secondary appears in top-5, so weighted ≈ primary; the divergence will become meaningful when hybrid retrieval lands.

Per-bucket weighted scores are printed in the test breakdown next to primary-only rates so trends across BM25 → hybrid promotions stay visible.

### Latency

Per case we record **two latencies**:

- **index-only**: `time.perf_counter` around `BM25Index.search(query, k=5)` directly. This is what the p95 gate measures, because that's the operation the SLO is about — if `bm25s` regresses, this number moves; tool-wrapper overhead can't mask it.
- **tool-level**: `time.perf_counter` around `await search_convictions(ctx, query, k=5)` — index call plus PassageHit construction, snippet generation, and any session/awaitable overhead. Reported alongside as overhead headroom; doesn't gate.

Before the timed loop, 5 throwaway `index.search` calls warm up bm25s caches so the first few cases don't skew p95 on a 29-sample run. The gate is **index-only p95 < 50 ms** (currently sub-millisecond — orders of magnitude under budget). Tool-level p95 typically sits in the low tens of milliseconds.

## What the breakdown looks like at runtime

```
=== retrieval_golden — recall@5 ===
  cross_lang   0/5   ( 0.0%)  weighted 0.00  mean idx  0.20 ms
  literal     15/16  (93.8%)  weighted 0.94  mean idx  0.18 ms
  topic        5/8   (62.5%)  weighted 0.62  mean idx  0.19 ms
  overall     20/29  (69.0%)  weighted 0.69  p95 idx  0.30 ms  p95 tool 12.4 ms
```

(Exact numbers vary run-to-run; the index-only p95 sits well under 1 ms on this corpus while the tool-level p95 reflects PassageHit construction + snippet generation overhead.)

Printed unconditionally each test run; pytest dumps stdout on failure so a regression surfaces with full diagnostics inline.

## Caveats and known fixture issues (for future hardening)

- **`cripto-tributacao-cross-doc`** is dual-primary per its own notes. The primary-only score counts it as a fail; the weighted score gives it 0.5 because the secondary returned at rank 3.
- **`fgc-cdb-pt-literal`** has two valid ids (CDB doc + LCI/LCA doc both cover FGC); currently passes under primary-only.
- **`bucket_alt` is set on one case** (`dividendo-obrigatorio-pt-topic`, also cross-language). The test code doesn't currently consume it; bucket-overlap reporting would be a small extension.
- **No fixture entry covers `crypto_taxation_brazil` as a primary**, only as a secondary. If hybrid retrieval starts winning the EN-headed crypto cases, the fixture should grow a dedicated primary case there.

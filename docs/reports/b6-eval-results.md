# B6 — BM25-only eval results

**Run date:** 2026-05-10
**Solution:** BM25-only retrieval (`app/services/search.py`).
**Companion to:** `docs/reports/b6-eval-methodology.md` (how cases were built, how they're tested, how scores are calculated). A future `b6.5-hybrid-eval.md` will mirror this shape for the BM25 + dense embeddings + RRF run.

## Run context

| Item                                          | Value |
|-----------------------------------------------|-------|
| Corpus                                         | 30 docs, 423 passages |
| Dated documents                                | 14 of 30 (passages with date: 202 / 423) |
| Fixture                                        | `tests/fixtures/retrieval_golden.yaml` — 29 cases |
| Fixture buckets                                | 16 literal / 8 topic / 5 cross_lang |
| Query languages                                | 17 PT / 8 EN / 4 ES |
| `k`                                            | 5 |
| Retrieval                                      | `bm25s` library, default `lucene` method, `k1=1.5`, `b=0.75` |
| Tokenization                                   | NFKD strip-accents → lowercase → `\W+` split; no stopwords, no stemmer |

## Headline

| Metric                                      | Value |
|---------------------------------------------|-------|
| Primary recall@5 (overall)                  | **20 / 29 = 69.0%** |
| Weighted score (overall)                    | 0.69 |
| Latency p95                                 | 1.8 ms |

## Per-bucket breakdown

| Bucket       | Primary recall@5 | Weighted | Mean latency |
|--------------|------------------|----------|--------------|
| `literal`    | 15 / 16 (93.8%)  | 0.94     | 0.7 ms       |
| `topic`      | 5 / 8 (62.5%)    | 0.62     | 0.7 ms       |
| `cross_lang` | 0 / 5 (0.0%)     | 0.00     | 1.1 ms       |
| **overall**  | **20 / 29 (69.0%)** | **0.69** | **p95 1.8 ms** |

At this baseline the **weighted score equals the primary score** — no failing case has its secondary id in top-5. The two scores will diverge once hybrid retrieval lands.

## Test gates (asserted)

| Gate                          | Floor | Current | Status |
|-------------------------------|-------|---------|--------|
| `literal` primary recall@5    | ≥ 90% | 93.8%   | ✓      |
| `topic` primary recall@5      | ≥ 50% | 62.5%   | ✓      |
| `cross_lang` primary recall@5 | reported only — not gated | 0.0% | n/a |
| Latency p95                   | < 50 ms | 1.8 ms | ✓      |

Cross-language is reported but not asserted. Per ROADMAP B6, cross_lang failures are the trigger for a hybrid-retrieval conversation, not for an automatic gate.

## Failed cases (9 of 29)

| Case ID                                    | Bucket      | Why |
|--------------------------------------------|-------------|-----|
| `pgbl-vgbl-diferenca-pt-literal`           | literal     | BM25 length-normalization preferred longer "tributação"-heavy passages over the focused expected one. The right *document* came back (3 of 5 hits are from `pgbl_vgbl_comparacao`); the right *passage* is not in top-5. |
| `jcp-mecanismo-pt-topic`                   | topic       | Paraphrase: query says "pagar acionistas", expected passage uses "JCP / juros sobre capital próprio". No shared content tokens. |
| `dividendo-obrigatorio-pt-topic`           | topic       | Expected heading is in English ("Mandatory Minimum Dividend"); PT query has no token bridge. Fixture flagged this as BM25-risk. |
| `cdb-impuestos-es-cross-lang`              | cross_lang  | "impuestos" ≠ "tributação"/"IR". Only token overlap is "CDB". |
| `dolarizacion-es-cross-lang`               | cross_lang  | "dolarización" ≠ "dollarization" as BM25 tokens. |
| `fondos-inmobiliarios-es-cross-lang`       | cross_lang  | "fondos" ≠ "fundos" — one letter off, BM25 sees as different tokens. |
| `pequenas-empresas-es-cross-lang`          | cross_lang  | Pure ES paraphrase against EN doc; "small caps" never appears in the query. |
| `cripto-tributacao-cross-doc`              | topic       | Dual-primary case (per fixture notes). Neither expected id reached top-5; rank 3 was a different `guia_completo_tributacao` passage (`#4-fundos…` vs the expected `#7-criptoativos…`). |
| `family-office-sucessao-cross-lang`        | cross_lang  | "sucessório" ≠ "succession". Only token anchor is "family office". |

8 of 9 failures are predictable consequences of BM25's token-only matching (5 cross_lang + 3 paraphrase). 1 (`pgbl-vgbl`) is a length-normalization artefact on a literal query.

## Reproducing

```
uv run pytest tests/tools/test_search_convictions.py::test_retrieval_golden -xvs
```

Per-bucket breakdown is printed every run.

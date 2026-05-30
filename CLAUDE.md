# 客源搜索 LeadFinder — Agent Guide

> B2B 客源搜索：从公开目录/展会名单挖掘海外护肤品**买家**（进口商/经销商/批发商），
> 抽取并验证联系方式 → 买卖家分类 → 打分 → 导出。本文件约束代码怎么写，**写代码前先读**。
> Keep this file tight. If a rule isn't load-bearing, delete it.

## Status
- `src/leadfinder/` is the **v2 target** architecture (below). Build new work there.
- Root `run.py`, `collect.py`, `detail.py`, `enrich.py`, `classify.py`, `validate.py`, `score.py`,
  `output.py` are the **v1 flat prototype** — reference only, being migrated. Do **not** extend v1;
  port its logic into the v2 layout.

## Commands
Standard toolchain (config lands with v2 scaffolding):
- Install: `uv sync` (or `pip install -e ".[dev]"`)
- Run: `uv run leadfinder --source beauty_west_africa --limit 20`
- Test: `uv run pytest` · single: `uv run pytest tests/unit/test_enrich.py -k cfemail`
- Lint/format: `uv run ruff check . && uv run ruff format .`
- Types: `uv run mypy src`
- **Architecture check: `uv run lint-imports`** (import-linter — enforces dependency direction; must pass)
- Full gate before PR: `ruff check . && mypy src && lint-imports && pytest`

## Architecture
Two halves joined by one typed record (`Lead`):

```
CRAWL  (queue + child jobs)              PROCESS  (ordered stages, drop-on-fail)
  source.fetch() ─┐                        classify -> verify -> enrich -> score
  detail  job  ───┼─► RawRecord ─►Lead─►   each Stage.process(lead) -> Lead | None
  enrich  job  ───┘   dedup BEFORE enrich;   (None = drop, logged with a reason)
                      cache/dedup key =       ─► writers (csv / json / xlsx)
                      canonicalized URL
```

Module layout — **dependencies point INWARD**; `domain/` imports nothing project-local:
```
src/leadfinder/
  domain/      # PURE. models.py (Lead, RawRecord, SCHEMA_VERSION) · protocols.py (ports) · enums.py
  sources/     # adapters implementing LeadSource (one file per channel) + _registry.py
  stages/      # adapters implementing Stage: classify, enrich, verify, score
  infra/       # http.py (cache+retry+throttle) · email_data/ (disposable/role/free) · writers.py
  config/      # per-source CSS/field schemas + scoring weights — DATA, not code
  pipeline.py  # THIN runner: wiring + queue loop only, no business logic
  cli.py
tests/{contract,unit,fixtures}
```
Allowed imports: `sources,stages,pipeline -> domain`; `sources,stages -> infra`; `pipeline -> infra`.
Forbidden: `domain -> anything project-local`; `infra -> stages|pipeline`; `* -> cli`. Enforced by `.importlinter`.

## The contracts (ports) — do not break these casually
```python
# domain/protocols.py
class LeadSource(Protocol):
    name: str
    def fetch(self, params: SearchParams) -> Iterable[RawRecord]: ...   # discovery only

class Stage(Protocol):
    def process(self, lead: Lead) -> Lead | None: ...                   # return None to DROP

class EmailVerifier(Protocol):
    def verify(self, email: str) -> Verification: ...                   # never raises on bad input

class Writer(Protocol):
    def write(self, leads: Sequence[Lead]) -> Path: ...
```
`Lead` / `RawRecord` (pydantic v2) in `domain/models.py` are the **single source of truth** for the
schema. Cross every boundary with these types — never loose dicts. On any field change, bump
`SCHEMA_VERSION` and add a one-line changelog note.

## Adding a new SOURCE (the workflow that matters most)
1. New `sources/<name>.py` implementing `LeadSource`. Put selectors/field-maps in `config/<name>.py`
   as DATA — never hardcode selectors in the adapter.
2. Register in `sources/_registry.py` (`SOURCES = {"<name>": <Adapter>}`). No edits elsewhere.
3. Add a saved fixture under `tests/fixtures/<name>/`; the parsing test runs offline against it.
4. The shared `tests/contract/test_lead_source.py` runs every registered source automatically — pass it.

Reuse the pipeline/stages unchanged. **If onboarding a source forces you to edit a stage, the seam is
wrong — stop and fix the abstraction, don't special-case.**

## Always
- Each source is a `LeadSource` adapter; each step is a `Stage`. A stage **never** knows another stage;
  they communicate only via the `Lead` passing through.
- Extraction is **deterministic-first**: JSON API > CSS-schema (selectors as config data). Use an LLM
  only for (a) build-time schema generation, (b) genuinely unstructured long-tail sources,
  (c) batched buyer/seller classification.
- Dedup **before** enrich, keyed on canonicalized website-domain + company-name (drop `utm_*`, sort
  query, lower host). The same canonical URL is the HTTP cache key.
- Handle errors **at boundaries**: an adapter catches its own network/parse errors and yields a typed
  result or one domain error.
- Keep `pipeline.py` to wiring only; extract logic into `_pipeline_internal/` the moment it grows.
- Public callables: keyword-only constructors (`def __init__(self, *, config, client)`); abstract
  param types (`Iterable`, `Mapping`), concrete return types. Positional order is a frozen contract —
  append new optional params, never insert.
- Private by default: new modules/helpers prefixed `_`; public surface is only what's in `__all__`.
  Import from the module file, not from a package `__init__.py`.

## Never
- `import` infra (httpx, bs4, pandas, dns, smtp) from `domain/`. No circular imports — use
  `from __future__ import annotations` + `if TYPE_CHECKING:`.
- Put business logic (classify/score/verify rules) in `pipeline.py`, `cli.py`, or I/O writers.
- Add an abstraction with one implementation and no test fake. Introduce a Protocol only when a 2nd
  impl or a fake needs it (resist premature abstraction; three similar lines beat a wrong base class).
- Leave dead code or commented-out blocks — delete it, git remembers. No bare `except:`, no silent
  fallbacks; fail fast and loud.
- Hit the live network in a unit test (use fixtures). Commit scraped contact PII, `cache/`,
  `data/output/`, `.env`, or API keys.
- Copy code from no-license repos. Vendored code/data must be permissive (MIT) with notice kept.

## Domain rules (don't regress these)
- The goal is **BUYERS** (importers/distributors/wholesalers/retail), not sellers. Manufacturers/brands
  are competitors → down-rank, never surface as top leads.
- Email role-direction is a buyer/seller signal: `purchasing@ buyer@ procurement@ import@` → buyer (+);
  `sales@ export@` → seller (−). A free domain (gmail) is a mild negative but **keep it** (African SMBs
  use webmail) — a feature, not a filter.
- Verification has 4 buckets: **Safe / Risky / Invalid / Unknown**. With SMTP off (default),
  MX-valid + non-role + non-disposable = **Unknown, keep it**. Unknown ≠ Invalid.
- Keep v1's edge in v2: Cloudflare `data-cfemail` decode + `/contact`,`/about` crawl + on-disk cache.

## Testing
- Test through the public interface; assert on outputs / dropped-records / raised errors. Never assert
  on private state — a behavior-preserving refactor must keep tests green.
- Prefer hand-written `FakeSource`/`FakeStage` over `unittest.mock`; mock only true external boundaries
  (live HTTP, SMTP/verify API). If a fake is hard to write, the Protocol is too big — shrink it.
- One contract suite per Protocol, run every implementation through it.

## Gotchas
- Beauty West Africa: list is a JSON handler `ExhibitorListHandler2025.ashx?...&q=~~~`, pageSize capped
  at 16; website is on the detail page, emails only on the company's own site.
- SMTP/catch-all checks need port-25 egress from a clean IP — gate behind a flag, run as a sidecar;
  default off → results are `Unknown`, not `Invalid`.
- Email data tables (disposable ~123k, free ~4.5k, role ~900) refresh daily from upstream JSON;
  don't hand-edit.

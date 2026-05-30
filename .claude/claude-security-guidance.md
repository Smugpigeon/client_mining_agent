# Security guidance — 客源搜索 LeadFinder

Threat model: this is a web scraper + contact-enrichment pipeline. It fetches
**untrusted** HTML/JSON from arbitrary external sites and stores third-party
contact PII (company emails/phones). Review Claude's changes against these rules.

- Treat all scraped/fetched content as untrusted input. Never `eval`, `exec`, or
  `pickle.loads` / `yaml.load` anything derived from a fetched page or API response.
- Never build shell commands, file paths, SQL, or URLs by string-concatenating
  scraped values. Pass an argv list to subprocess; never `shell=True`.
- SSRF: never fetch a URL taken from scraped content without validating scheme/host.
  Reject non-`http(s)` schemes and internal/link-local/private IPs.
- Secrets (`HUNTER_API_KEY`, any provider keys) come from env / `.env` only — never
  hardcode, never log. Do not commit `.env`, `cache/`, or `data/output/`.
- Contact PII must not be logged at INFO+ or printed in full in shared logs. Put
  aggregate counts in summaries, not raw emails/phones.
- Every outbound HTTP call sets an explicit `timeout`; never disable TLS verification
  (`verify=False` is forbidden).
- Do not add code that bypasses robots.txt or the configured rate limits.

# EvalGuard

**pytest for your prompts.** EvalGuard is a CLI that turns LLM prompts and agent behavior into a
regression test suite you run before every deploy — so a prompt tweak that quietly breaks
classification accuracy, drops a required disclaimer, or starts hallucinating gets caught in CI,
not by your first angry customer.

```
✓ password-reset          90.0%
✓ dashboard-crash-bug      83.3%
✗ account-breach-security   0.0%   <- caught before it shipped
✓ invoice-discrepancy     100.0%
```

## The problem

LLM prompts are code, but almost nobody tests them like code. A "small" wording change to a
system prompt, a model upgrade, or a new few-shot example can silently:

- Flip a classification decision that downstream logic depends on
- Drop a required disclaimer, safety caveat, or escalation path
- Make an agent stop calling a tool it used to call reliably
- Degrade tone, or start hallucinating facts

None of this throws an exception. Nothing fails a build. It just quietly ships, and you find out
from a support ticket, a bad review, or a compliance incident — long after the prompt change
that caused it is buried in git history.

**The cost of a bad prompt in production isn't hypothetical**: wrong answers erode trust faster
than a slow page load, hallucinations create liability, and an agent that stops escalating a
security-relevant ticket (see the `account-breach-security` case in the example dataset below) is
a real incident, not a demo bug. Most teams have zero automated coverage for this today — prompts
live in strings, get edited in place, and ship on vibes.

## What EvalGuard does about it

EvalGuard treats a prompt + expected behavior as a test case, runs it through your LLM provider,
scores the response against explicit criteria, and fails the build if quality drops below a
threshold you define. It's the same shape as a unit test suite — just aimed at model behavior
instead of function return values.

1. Define cases in a JSONL dataset: inputs + expected output/criteria.
2. Render each case through a Jinja2 prompt template.
3. Run it through your LLM provider (ships with a deterministic `MockLLM`; plug in a real one in
   a few lines — see below).
4. Score the response with `exact_match`, `contains`, `regex_match`, or `keyword_overlap`.
5. Get an HTML report to look at and a JSON report your CI pipeline can gate on.

## Quickstart (under a minute)

```bash
git clone <this-repo> evalguard && cd evalguard
make install
evalguard run examples/config.yaml
```

That's it — no API key required, because the bundled example runs against `MockLLM`. You'll see a
live results table in your terminal, and two reports written to `reports/`:

- `reports/report.html` — a clean, dark-themed dashboard you can open in a browser
- `reports/report.json` — machine-readable, built for CI (see **CI usage** below)

The example dataset is deliberately realistic: 10 customer-support tickets, some of which the mock
model handles well and some it doesn't (a generic pricing question, a cancellation flow, and — the
one that matters — a suspected account breach that gets a generic password-reset reply instead of
a security escalation). That's the point: a fake "100% passing" demo teaches you nothing about
whether the tool actually catches regressions. This one does.

## What the HTML report looks like

The report opens with a pass/fail gate banner (score ring + threshold), four summary stat tiles
(total / passed / failed / overall score), then an expandable list of every case showing the
rendered prompt, expected criteria, actual model response, and a breakdown of which evaluator(s)
passed or failed and why. Dark theme, monospace for prompts/responses, color-coded pass/fail
throughout — designed to be something you'd actually paste into a PR description, not a wall of
raw text.

*(Run `evalguard run examples/config.yaml` and open `reports/report.html` to see it live — a
static screenshot would go stale the moment the template changes.)*

## Writing your own eval suite

### 1. A config file (`config.yaml`)

```yaml
name: my-support-bot-suite

provider:
  type: mock          # swap for a real provider once you've written one — see below
  model: mock-llm-v1

prompt:
  template_path: prompt.jinja   # or use `template: "inline {{ jinja }}"` instead

dataset_path: dataset.jsonl

evaluators:
  - type: contains
    weight: 1.0
    options:
      case_sensitive: false
  - type: keyword_overlap
    weight: 1.0
    options:
      min_overlap: 0.3

min_score: 0.75        # CI gate: exit code 1 if the overall score falls below this
report_dir: reports
```

### 2. A dataset (`dataset.jsonl`), one JSON object per line

```jsonl
{"id": "refund-request", "description": "Customer asks for a refund", "inputs": {"topic": "a refund", "customer_message": "I was charged twice, please refund me."}, "expected": {"value": ["refund", "billing team"], "reference": "refund flagged billing team"}}
```

- `inputs` — variables injected into your Jinja2 prompt template
- `expected` — criteria consumed by whichever evaluator(s) you configured:
  - `exact_match` / `contains` read `expected.value` (a string, or a list of required substrings)
  - `regex_match` reads `expected.pattern`
  - `keyword_overlap` reads `expected.reference` (falls back to `expected.value`)

### 3. Evaluators available today

| Evaluator | What it checks |
|---|---|
| `exact_match` | Response equals `expected.value` (case-insensitive by default) |
| `contains` | Every required substring in `expected.value` is present |
| `regex_match` | `expected.pattern` matches somewhere in the response |
| `keyword_overlap` | Fraction of `expected.reference` keywords (stopwords stripped) found in the response — a lightweight semantic-overlap proxy that needs no embeddings or extra dependencies |

Each evaluator returns a 0–1 score; multiple evaluators on the same case are combined with
`weight`-averaging. A case passes when its combined score clears `min_score`; the whole run passes
when the *average across all cases* clears `min_score`.

### 4. Run it, and gate CI on the exit code

```bash
evalguard run config.yaml
echo $?     # 0 = overall score >= min_score, 1 = below threshold, 2 = config/run error
```

Wire that straight into a GitHub Actions step (or any CI) — no plugin required:

```yaml
- run: pip install -e .
- run: evalguard run examples/config.yaml
```

### 5. Scaffold a new project fast

```bash
evalguard init my-new-suite
```

Copies a starter `config.yaml` and `dataset.jsonl` into `my-new-suite/` so you're editing instead
of starting from a blank file.

## Plugging in a real LLM provider

`MockLLM` ships as the default so the tool runs with zero setup and zero API cost, but it was
built from day one behind an interface so a real backend is a small, additive change:

```python
# evalguard/providers/openai_llm.py
from evalguard.providers.base import LLMProvider

class OpenAIProvider(LLMProvider):
    def complete(self, prompt: str) -> str:
        import openai
        client = openai.OpenAI(api_key=self.options["api_key"])
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
```

Then register it and point your config at it:

```python
# evalguard/providers/registry.py
from evalguard.providers.openai_llm import OpenAIProvider
PROVIDERS["openai"] = OpenAIProvider
```

```yaml
provider:
  type: openai
  model: gpt-4o-mini
  options:
    api_key: ${OPENAI_API_KEY}
```

Nothing else in the pipeline (dataset loading, templating, evaluators, reporting) needs to change
— that's the whole point of the interface.

## The frontend report viewer

`frontend/index.html` is a single self-contained file (no build step, no server) that renders the
same dashboard as the CLI's HTML report, but takes a `report.json` as input — drag-and-drop it, or
paste the raw JSON. Useful for sharing a report with someone who doesn't have the repo checked
out, or for building a lightweight "upload your CI artifact here" internal tool without shipping a
backend. Open it directly with `file://` — it reads the file via `FileReader`, so there's no CORS
issue and nothing leaves your browser.

## Why EvalGuard (vs. the alternatives)

- **vs. manually eyeballing outputs**: eyeballing doesn't scale past a handful of cases, doesn't
  run in CI, and doesn't leave an audit trail of what passed before a change and what broke after
  it. EvalGuard turns "I re-ran a few prompts and it looked fine" into a diffable, versioned report.
- **vs. no testing at all**: this is the default state for most LLM features today, and it's the
  same as shipping application code with no test suite — it works until the one time it silently
  doesn't, and you find out from a user instead of a CI failure.
- **vs. building this in-house**: you'll end up rebuilding config loading, dataset parsing,
  scoring, and reporting anyway — EvalGuard gives you all four today, with a clean provider
  interface so it isn't locked to any one model vendor.

## Development

```bash
make install     # creates .venv and installs evalguard + dev dependencies
make test         # runs the pytest suite
evalguard run examples/config.yaml    # runs the bundled example end to end
```

Project layout:

```
evalguard/
├── cli.py                 # Typer commands: run, init
├── config.py               # Pydantic config models + YAML loader
├── dataset.py               # JSONL dataset loader
├── evaluators.py             # exact_match, contains, regex_match, keyword_overlap
├── runner.py                  # orchestrates render -> generate -> evaluate -> aggregate
├── report.py                   # JSON + HTML report generation
├── providers/
│   ├── base.py                  # LLMProvider interface
│   ├── mock_llm.py                # deterministic default provider
│   └── registry.py                 # provider_type -> class lookup
└── templates/
    └── report.html.jinja           # HTML report template

examples/        # realistic config + dataset + prompt template used by `evalguard run`
frontend/        # standalone JSON report viewer (index.html)
tests/           # pytest suite (config, dataset, evaluators, mock LLM, CLI end-to-end)
```

## License

MIT — see [LICENSE](LICENSE).

# Evals

How we will know the server answers from NHTSA's data instead of from the model's habits. Nothing here runs yet. This is the design the implementation has to meet.

The first sketch said "golden-set evals" and "a CI gate" as if those were one system. They should be two. CI can gate facts we can recompute with no network and no model. A live model is a different measurement, run locally, with a key that never enters the repo or the CI logs.

## What a case is

A case is a user question, a frozen picture of the NHTSA responses that question depends on, and a statement of what a good run does.

```text
case
  id
  category
  user_question
  fixtures: named upstream responses the tools would have seen
  expected:
    tool: name
    arguments: normalized
    answer_must_include: strings that have to appear
    answer_must_not_include: strings that must not appear
    profile_fields: a subset of the shaped JSON, when the case is about the shaper
```

The model is not graded on prose style. It is graded on whether it called the right tool, passed arguments that identify the same vehicle, and said only things the fixture supports.

## Categories

Start with about 40 cases. That is enough to cover the failure modes we already saw, and small enough to read in review. Grow it when a real mistake shows up, not in advance.

| Category | What it protects | Example we can already write |
| --- | --- | --- |
| `decode_ok` | A clean decode is quoted, not embellished | Blocked on capturing an `ErrorCode` 0 fixture. We did not observe one in research. |
| `decode_partial` | Incomplete VIN stays a warning | The documented `5UXWX7C5*BA` returns code 6 and still names a 2011 BMW X3. The answer may use the name and must show the warning. |
| `decode_invalid` | Garbage is not repaired into a car | `ABC` returns codes 6, 7, and 11. The answer says it did not decode. |
| `decode_check_digit` | A check-digit warning is not hidden | `3GNDA13D76S000000` returns code 1 and still describes a Chevrolet HHR. |
| `missing_means_unknown` | Empty specs are not turned into "not equipped" | The BMW flat decode has 116 empty keys. The answer must not say the car lacks a feature whose field was empty. |
| `not_applicable_dropped` | The shaper removes sentinels | Bus and trailer fields were `Not Applicable` on that SUV. They must not appear in the default decode. |
| `recalls_hit` | Campaign facts match the fixture | Acura RDX 2012 returned two campaigns. Quote the campaign number from the fixture, not from memory. |
| `recalls_spelling` | An empty list is not "no recalls" | BMW X3 was missing from the products model list and present in the recalls API. A case where the first spelling is empty and `list_model_names` has another. |
| `recalls_not_repair_status` | The model does not claim the VIN was fixed | Any recall case. `answer_must_not_include` a phrase like "has been repaired." |
| `complaints_summary` | Counts, not narratives | The Civic 2018 body was 596 rows. The tool result the model sees is the summary. The answer uses those totals. |
| `complaints_redaction` | VIN and narrative stay out | The shaped fixture has no `vin` field. A judge that sees a VIN-shaped token fails the case. |
| `ratings_not_rated` | `Not Rated` stays words | Vehicle 7520, the id in NHTSA's own example, was Not Rated. The answer must not call it five stars or zero stars. |
| `ratings_variant` | The model does not pick a drivetrain in silence | 2013 RDX has FWD and AWD ids. |
| `profile_partial` | One dead upstream does not blank the rest | A fixture where complaints time out and recalls return. `section_status` is the ground truth. |
| `out_of_scope` | Title history, fuel economy, repair status | The model should say the server does not have it, and should not call a tool with a made-up argument. |
| `investigation_link` | A campaign's action number can be looked up | The Acura recall row included `NHTSAActionNumber` `EA15001`. Needs a frozen slice of the investigations file, not a live download in CI. |

Forty cases across these categories, several per row, is the v1 set. The exact questions get written when the first fixtures are captured, because the expected strings have to be copied from the fixture, not from this prose.

## Ground truth

Ground truth is a file in the repo, not a live call and not the model's recollection.

1. A maintainer runs a capture command locally. It calls NHTSA once, writes the raw JSON, and writes the shaped JSON the tool would return.
2. The capture strips complaint `vin` and `summary` fields before writing. It records `count` and the aggregate numbers. It does not keep narratives in git.
3. The file's header stores the URL, the UTC time, and the git commit of the shaper. Reviewers can see when a fixture changed.
4. Tests load the file. They do not resolve DNS.

Fixtures go stale when NHTSA updates a campaign. That is a content change, not a test failure to "fix" by loosening the assert. Refreshing a fixture is a reviewed edit. CI should fail if someone deletes the fetch timestamp.

We will not check in the 577 KB Civic body. The complaint fixture is the summary plus a tiny synthetic row used only for the redaction unit test, with a fake VIN we invented for the test (`"VIN": "1HGCM8263********"` is still too close to a pattern; use an obvious placeholder like `REDACTEDVIN` and assert the shaper removes a field named `vin` regardless of contents).

Investigations fixtures are a few dozen lines cut from the public flat file, enough to join `EA15001` if that id is actually in the file. We have not opened the zip. The id was on a recall record. Confirming it is in `FLAT_INV.zip` is build work, not a claim.

## Metrics

Report them separately. A single score hides a model that calls the right tool and then invents a remedy.

| Metric | How it is scored | Gate |
| --- | --- | --- |
| Tool selection | The first meaningful tool equals `expected.tool`. Asking `list_model_names` before a retry can be allowed per case. | Deterministic. CI. |
| Argument correctness | Normalized arguments equal the expected set. Make and model compared case-insensitively. Extra arguments fail. | Deterministic. CI, on scripted traces. |
| Field accuracy | Shaped JSON matches the fixture's expected subset. | Deterministic. CI. No model involved. |
| Faithfulness | Every factual claim in the final answer is supported by the tool result. Unsupported claim fails. | Model-judged. Local only. |
| Hallucination of absence | Saying a feature is missing, a recall does not exist, or a car is unrepaired, when the tool did not say that. | Both. Scripted checks for known bad phrases in CI. A judge locally for paraphrases. |
| Latency | Server time to produce the shaped tool result, fixtures in memory, no network. | Reported. A budget, not a failing assertion at first. Profile under 50 ms locally is a reasonable target and was not measured. |
| Token cost | Estimated tokens of the tool result the model would see. | Reported. The architecture budgets are the reference. CI fails if a fixture's shaped output exceeds its budget, using a simple character estimate (characters divided by 4) until we pick a tokenizer. |

Tool selection and arguments can only be a CI gate if the "model" in CI is a script. A script that, given category `recalls_hit`, emits the expected tool call, proves the scorer. It does not prove that Claude or GPT will call the tool. Those runs are the local eval. Pretending otherwise is how a green build stops meaning anything.

## Deterministic and judged

**Deterministic, in CI, no network, no key.**

- Unit tests for the shaper: drop empties, drop `Not Applicable`, convert `30/10/2017` to `2017-10-30`, refuse to convert an ambiguous date without a comment in the fixture, clip summaries, strip `vin`, aggregate complaints.
- Contract tests: each fixture loads, the tool function returns the expected subset, `section_status` is right on the partial-failure fixture.
- Budget tests: shaped fixtures sit under the token estimate.
- A fake-model trace runner: for each case, feed a canned tool call, run the server in-process, score argument checks and the must-include list against a canned final answer that we also store. This locks the scorer. It is not a model eval. Name it that way in the README so nobody quotes it as accuracy.

Threshold: 100 percent of the deterministic tests. They are assertions about our code and our files. A 95 percent bar would mean we are willing to ship a shaper that drops a campaign. We are not.

**Judged, on a laptop, with a key in `.env`.**

- A runner starts the server on stdio against the fixture transport (the tools read fixtures, not NHTSA).
- The user's model receives the question and the tool list.
- We record the tool trace and the final answer.
- A second call, or a deterministic rubric where it is enough, scores faithfulness: claims must be entailed by the tool JSON. The rubric is written down next to the case, not improvised in the scorer.
- Results append to a local report. A maintainer may commit a summary table to the docs. They may not commit the key, the raw provider payload, or complaint text.

Suggested targets for that local run, once 40 cases exist: tool selection at or above 90 percent, argument correctness at or above 90 percent on the cases where the tool was right, and zero faithfulness failures on the `must_not` list. These are targets to publish, not CI. A model change would make a CI judge flap, and this repo will not have a secret to call a model in GitHub Actions.

If the local run is below the target, the fix is usually a tool description or a smaller payload, not a longer prompt. That is the Context Engineering loop: change the context the model sees, rerun the same cases, keep the change only if the numbers move.

## Frameworks

We compared four approaches against this specific need (a stdio MCP server, frozen HTTP fixtures, a CI job with no secrets, and an optional local model).

| Option | What it gives us | Why it is or is not the gate |
| --- | --- | --- |
| A small pytest harness in this repo | Loads fixtures, runs the shaper, checks scripted traces, prints a JSON report. No account. | This is the CI gate. It is a few hundred lines when we build it, which is less code than a framework adapter. |
| [Inspect AI](https://inspect.aisi.org.uk/tools.html) | A real agent loop, MCP tools, datasets, scorers, and error bars on repeated trials. Python. | Best optional runner for the local model pass. We did not find, in the pages read for this design, a documented "fail the pull request" product built around it. Use it locally. Do not make CI depend on it. |
| promptfoo | YAML cases, assertions, and, according to a [2026 comparison](https://www.evalshift.dev/blog/best-llm-evaluation-tools), trajectory checks and a GitHub Action. Node. | A good fit if we want to compare two models on the same 40 cases. We did not re-read promptfoo's own docs in this pass, so the trajectory claim is second-hand. Re-read before adopting. It still needs a provider key, so it is not the secret-free gate. |
| DeepEval | pytest-shaped metrics, including agent metrics. A [2026 MCP eval roundup](https://www.mcpjam.com/blog/best-mcp-evals-tools) describes `MCPUseMetric` modes that call another vendor's model unless you bring an LLM. | More machinery than the gate needs, and a path that can quietly require a second API key. Skip for v1. |

Inspect is the one to reach for when the scripted tests are green and we want a real model in the loop. The custom harness stays the thing CI runs. Adding promptfoo later is a config file on top, not a rewrite, if its trajectory assertions still match the docs when we look.

## Local run

```text
cp .env.example .env
# put a key in .env. the file is gitignored.

uv run pytest                 # no key, no network
uv run python -m evals.local  # reads .env, uses fixtures, calls the model
```

`evals.local` refuses to start if it cannot see a key, and it refuses to start if a test tries to open a socket to `nhtsa.gov`. The fixture transport is the only HTTP implementation in that process. A test that patches poorly and calls the network should fail closed.

The model name comes from `EVAL_MODEL`, then from a default we document (one current small model, chosen at build time, not in this design). The report header prints the model id and the date. Results from different models are not pooled.

## CI

GitHub Actions, on pull request and on push:

1. Install from the lockfile with uv.
2. `pytest` for shaper, contracts, budgets, and scripted traces.
3. A test that the suite contains no network socket. This can be a subprocess with `socket` blocked, or a simple grep of the test tree plus a unit test that the tool client's base URLs are the fixture ones when `GLOVEBOX_FIXTURES` is set.
4. No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the workflow. If one is present in the environment, the job does not use it.

The job fails if any deterministic test fails. There is no flake budget. There is no coverage percentage gate in v1. Coverage of the shaper matters more than a number, and the fixtures are that coverage.

A nightly job that calls live NHTSA and diffs fixtures is tempting and out of scope until v1 is stable. It would spend NHTSA's capacity from a data center and it would fail whenever a new recall is filed, which is the data working as intended. Refresh fixtures by hand.

## Publishing results

The README gets two blocks, and only two:

1. CI: "Contract tests: passing on `<sha>`" with a link to the workflow. This can be a badge.
2. Maintainer model run: a small table, date, model, n cases, tool-selection rate, argument rate, faithfulness failures, and the median estimated tokens of `vehicle_profile`. Under the table, one line: these numbers are not the CI gate, and the method is in `docs/evals.md`.

Do not publish a leaderboard. Do not publish raw model output that might repeat a complaint narrative. The committed report is the table.

## What this design refuses

- A CI job that calls NHTSA.
- A CI job that calls a model.
- A golden answer stored only inside a prompt.
- A metric that rewards a fluent paragraph which did not use the tool.
- Copying another project's test suite. The cases come from the public responses we captured and from the failure modes in the data inventory.

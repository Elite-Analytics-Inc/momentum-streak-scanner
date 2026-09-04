# rules.md — the shape of an analysis repo

*The technical reference for the agent. The analyst never needs this file; the agent always does.
Where these rules and the worked example seem to disagree, the example is right — it ran.*

## The repo, after the interview

The interview generates everything below the line; the template shipped only the guidance, the
local SDK stand-in, and the examples. Nothing here is a stub — if a file exists, it is real.

```
├── CLAUDE.md            guidance (shipped; permanent — it guides every later visit)
├── rules.md             this file (shipped; permanent)
├── pyproject.toml       the pinned environment: the platform SDK + renderer, the design
│                        system, the engine (shipped; `uv sync` builds it — see "Running")
├── tarn_draft-*.whl     the platform's own package, which came inside the starter download
│                        (shipped; private — gitignored, it never enters the repository)
├── example/             the worked example — complete, working, never edited (shipped)
├── example-multipage/   what a multi-page dashboard looks like (shipped)
├── .gitignore           (shipped)
│   ── everything below is generated during the interview ──
├── spec.md              the analysis specification — the living source of truth
├── README.md            plain-English summary, derived from spec.md, never edited directly
├── main.py              the analysis, run top to bottom
├── parameters.json      the run contract: meta / lineage / parameters / resources
├── dashboard/           the dashboard pages (markdown)
├── data/                input data (real or fabricated), see the hierarchy below
└── output/              what a run writes: one parquet per output, plus dashboard/ (gitignored)
```

## The data folders

Inputs live under `data/<catalog>/<namespace>/<table>/*.parquet`:

- **The catalog is `lake`** — the same name the platform gives the governed workspace, so SQL
  written here (`lake.banking.members`) is the SQL that runs unchanged after promotion.
- **The namespace** groups related tables (a bank's book might be `banking`); **the table** is
  one dataset; the parquet files inside are its rows.
- **Parquet only, never CSV.** Parquet keeps column types. A CSV would quietly turn `06196` into
  `6196` — exactly the class of surprise a draft exists to catch early, not to cause.

## The Job Definition contract

An analysis is a plain Python project with exactly this shape — it is what the platform registers
and runs, and `example/` conforms to every point:

- **`main.py` runs top to bottom.** No framework, no DAG, no hidden entry points. One file a
  human reads from the first line to the last.
- **`parameters.json`** declares, in four sections: `meta` (name, description, owner), `lineage`
  (the datasets read, as `{namespace, table, mode: "read"}`), `parameters` (each typed, described,
  with a default and bounds — these render the launch form), and `resources` (cpu/memory
  requests and limits, `timeout_minutes`, pool). Copy the example's and adapt; do not invent
  fields. **The platform reads this file out of the built package at registration** — it is the
  contract, and nothing in it is retyped — so it must say the whole truth.
- **An analysis that reads no dataset says so:** `"lineage": {"datasets": [], "reads_nothing":
  true}`. That is a declaration the platform honours (the run gets no read credential at all).
  An empty `datasets` list *without* the flag is refused at registration, because empty by
  omission and empty on purpose must never look the same.
- **Parameters arrive as environment variables** named `TARN_PARAM_<NAME>` (uppercased), read at
  the top of `main.py` with the same defaults `parameters.json` declares. The workspace catalog
  name arrives as `TARN_WORKSPACE_CATALOG` (default `lake`) — read it, never hardcode it.
- **`dashboard/`** holds the dashboard markdown (below).

## The SDK (the real one — there is no stand-in)

The analysis imports **`tarn`** — the actual platform SDK, installed by `uv sync` from the
wheel that came inside this starter download, built by the platform it will promote into. One
SDK, two grounds: run by `tarn-draft run` it works locally — the lake is the parquet under
`data/`, outputs land in `output/`, events narrate to the terminal; run as a promoted job the
identical calls reach the governed lake with the launching user's row filters and masks
applied. **The draft's `main.py` is already written the way the promoted job runs**,
and promotion changes nothing about the code — there is no second implementation to diverge.

The calls, as the example uses them:

- `tarn.stage(name)` / `tarn.log(msg)` / `tarn.progress(fraction, msg)` — narrate the run.
- `tarn.save_artifact(name, sql)` — **the output door.** One SQL query, one named result the
  dashboard reads. Push the work into the SQL; keep Python for orchestration.
- `tarn.save_dashboard()` — ship `dashboard/` with the output, exactly as written.
- `tarn.conclusion(text)` — one sentence of what the numbers said.
- `tarn.fetch(name, sql)` / `tarn.connect()` — scratch space for shaping, when a single query
  genuinely cannot express the step. Prefer `save_artifact` with better SQL.

**Learn the usage from `example/main.py`, not from memory** — it demonstrates the patterns as
they are meant to be used: parameters read once at the top, a shared derivation as CTEs repeated
into each output's query, one `save_artifact` per output, the dashboard shipped last.

## The SQL the platform's doors accept

Every `tarn.fetch(name, sql)` and every `tarn.save_artifact(name, sql)` is sent to the platform's
engine and checked before it runs. The local ground does **not** apply this check yet, so a query
that runs on the laptop can be refused in the pod. Write to the rules from the start:

- **One SELECT.** No writes, no second statement, no `ATTACH`, no `SET`.
- **Scalar and aggregate functions only.** Arithmetic, string, date, math (`exp`, `ln`, `log`,
  `power`, `round`), window functions and aggregates are fine.
- **Never a function used as a table.** `FROM range(1, 11)`, `FROM generate_series(...)`,
  `FROM read_parquet(...)`, `FROM unnest(...)` are all refused as "unrecognised syntax". A number
  series is written as a scalar: `SELECT unnest(generate_series(1, 10)) AS year_index`, and a
  literal list as `SELECT unnest([1, 2, 3]) AS n`. Verified against the platform's door
  2026-09-02: the table forms refuse, the scalar forms pass.
- **Tables are `lake.<namespace>.<table>`**, the same spelling in both doors. No file paths, no
  settings readers, no introspection built-ins.

The first analysis promoted from a Draft (2026-09-02) passed every local run and was refused in
the pod on `FROM range(...)`. Until the local ground carries the check, this list is the check.

## Dashboards

Markdown pages in `dashboard/`, each made of fenced SQL blocks (which read the outputs by name)
and widget tags that reference those blocks. Two references, two different jobs — use both:

- **The vocabulary is the installed widget reference — authoritative, never invent beyond it.**
  The plume package this environment installs ships `WIDGETS.md`: every tag, every attribute,
  the data shape each widget's SQL must produce, when to use it, snippets, pitfalls. It is
  generated from the renderer's own code, so it describes exactly what this environment can
  draw — trust it over memory, always. Read it before designing a dashboard:
  `uv run python -c "import plume, pathlib; print(pathlib.Path(plume.__file__).parent / 'WIDGETS.md')"`
- **The craft standard is the examples.** `example/dashboard/index.md` (single page) and
  `example-multipage/dashboard/` (an overview plus numbered chapters with `title` and
  `sidebar_position` frontmatter) show what good looks like: a note above every section saying
  how to read it, formats on every number, a glossary for every term of art. The reference says
  what is *possible*; the examples say what is *good*.

## Running the draft (and showing the dashboard)

Everything runs through **uv**, from the repo root, and the analyst never types any of it:

- **`uv sync`** — once, at the tools gate: builds the pinned environment (the exact Python
  version, the platform SDK and renderer, the design system, the engine). This is the install
  the one-line ask covers.
- **`uv run tarn-draft run`** — runs `main.py` on the local ground, then serves the dashboard
  at a local address and opens the browser. **This is how stage 9 ends: with the analyst
  looking at their dashboard**, rendered by the same code the platform renders with. Add
  `--no-preview` to run the analysis alone; `uv run tarn-draft preview` re-opens the dashboard
  without re-running. **Several analyses at once are fine:** each folder's preview takes the
  next free port when the usual one is held by another, says so in its first line, and opens
  its own address; the browser tab is titled with the folder's name. Always hand the analyst the
  address the command printed, never one remembered from an earlier run.
- Anything else the analysis itself needs is added with `uv add <package>` after its own
  one-line ask, and recorded in `spec.md`.

Outputs land in `output/`: one parquet per `save_artifact`, plus the shipped `dashboard/`.
Sample numbers in chat are for the small confirmations along the way; the dashboard in the
browser is the payoff.

## Honesty rules

- Fabricated data is scaffolding. **Green on pretend data is not green on real data** — the real
  acceptance is a later run against the real thing, and the analyst should never be led to
  believe otherwise.
- `output/` is generated; never hand-edit it. `example/` is the known-good original; never edit
  it at all.
- The `README.md` is derived from `spec.md`, one way, always. If they could disagree, the spec
  wins and the README is regenerated.

## Democratize the knowledge

The reader of a dashboard is not its author, and the founding philosophy is that they should
not need the author in the room: the page itself untangles its own jargon and teaches the
reader to judge what they see.

Two obligations, on every page, non-negotiable:

1. **A vocabulary.** Every term of art the page uses — the domain's words (DPD, vintage,
   structuring, NSF) and the analysis's own words (at risk, flagged, window, floor) — is
   defined in a `{% glossary %}` near the top. If a word would make a new branch manager
   reach for a search engine, it belongs in the glossary. And not only the page's own
   coinages: the **surrounding context** that lets a reader comprehend with support — the
   regulator watching this area, the law that scores it, the standard fee or threshold the
   industry assumes — earns an entry too. "CFPB — the regulator pressing on overdraft fees
   since 2022" turns a chart into a judgment; a reader who has to ask what CFPB stands for
   was left outside the room.
2. **An ⓘ on every chart and tile.** `info=` says what the visual shows *and how to judge
   it* — what a rising line means, what would be worrying, what to compare against. Not a
   caption restating the title: the sentence a colleague would say while pointing at it.
   Section `{% notes %}` set context; the ⓘ rides the widget the reader is looking at.

The worked example models both — inherit the pattern in every page you write, including new
pages added to an existing analysis.

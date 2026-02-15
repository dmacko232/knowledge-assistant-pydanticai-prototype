# AI context: CLAUDE.md and Cursor rules

Best-practice locations and what to put in them (from Cursor/Claude docs and community).

---

## Where to keep them

| File / folder        | Location              | Purpose |
|----------------------|-----------------------|--------|
| **CLAUDE.md**        | **`.claude/CLAUDE.md`** | Project-level instructions for Claude (and Cursor). Commit it so the whole team gets the same context. |
| **CLAUDE.md.local**  | `.claude/`            | Your personal overrides (e.g. `.claude/CLAUDE.md.local`). Add to `.gitignore` so it’s not committed. |
| **Cursor rules**     | **`.cursor/rules/`**  | Cursor-specific rules. Use `.mdc` files (one per topic). Commit for team consistency. |
| User-level rules     | Cursor Settings → Rules | Your own global rules (all projects). |

**Summary**

- **CLAUDE.md** → **`.claude/CLAUDE.md`** (we use this layout)
- **Cursor rules** → repo root: `./.cursor/rules/*.mdc`
- Alternative: `./CLAUDE.md` at project root also works; both are read by Cursor/Claude.

---

## CLAUDE.md – what to put there

Keep it short; every line competes with the rest of the context.

1. **Project overview**  
   One short paragraph: what the project is and main tech stack.

2. **Commands**  
   The commands the AI should use (run, test, lint, format, DB, etc.).  
   Example: “Run tests with `make test` from repo root”, “Format with `make format`”.

3. **Project structure**  
   Main dirs and what they’re for (`data_pipeline/`, `docs/`, etc.).

4. **Code style and conventions**  
   - Imports (absolute vs relative)  
   - Naming (e.g. PascalCase for classes, snake_case for functions)  
   - Formatter/linter/type checker and how to run them  
   - Patterns to follow (e.g. “Use SQLModel for DB models”)

5. **Gotchas**  
   Things that are easy to get wrong: env vars, API quirks, files not to edit by hand, etc.

We keep `CLAUDE.md` in `.claude/CLAUDE.md`; refine these sections as needed.

---

## Cursor rules (`.cursor/rules/*.mdc`) – what to put there

Use **one file per concern** (e.g. testing, formatting, API usage). Cursor can auto-attach rules by file path (globs) or you can reference them with `@rule`.

**Basic structure of a rule file:**

```markdown
---
description: Short summary (shown in Cursor)
globs: ["data_pipeline/**/*.py"]   # optional: when to auto-include
alwaysApply: false                  # true = include in every chat
---

# Rule title

- Bullet points or short paragraphs.
- Be specific: "Use absolute imports" not "imports should be clean."
```

**What to put in rules (basics):**

- **Naming and style**  
  File/folder names, naming for functions/classes/variables, line length, quotes.

- **Testing**  
  Where tests live, how to run them, fixture location, “write tests for new code”.

- **APIs and env**  
  How config and env vars are used, which endpoints matter, no hardcoded secrets.

- **Project-specific**  
  “Chunking is section-based; retrieval chunk is preprocessed, generation chunk is raw section.”

- **Don’t**  
  “Don’t change X without Y”, “Don’t commit .env”.

**Example rule (e.g. `.cursor/rules/data-pipeline.mdc`):**

```markdown
---
description: Data pipeline code style and patterns
globs: ["data_pipeline/**/*.py"]
alwaysApply: false
---

# Data pipeline

- Use absolute imports: `from database.models import ...`, never `from .models import ...`.
- Run quality checks with `make check-all` from repo root.
- Chunking: one DB chunk per section; split section only if over token limit. Retrieval chunk = preprocessed for embedding; generation chunk = full section (raw).
- Embedding config: use env vars from config (AZURE_OPENAI_EMBEDDING_*). Load .env from data_pipeline via config.py.
```

---

## Quick checklist

- [ ] **CLAUDE.md** in **`.claude/CLAUDE.md`**, committed.
- [ ] **Cursor rules** in **`.cursor/rules/`** as **`.mdc`** files, committed.
- [ ] **CLAUDE.md** has: overview, commands, structure, style, gotchas.
- [ ] **Rules** are specific, one topic per file; use `globs` or `alwaysApply` when useful.
- [ ] **CLAUDE.md.local** in `.gitignore` if you use it.

This repo already has a root `CLAUDE.md`. Add `.cursor/rules/*.mdc` when you want Cursor-specific, scoped instructions (e.g. per directory or file type).

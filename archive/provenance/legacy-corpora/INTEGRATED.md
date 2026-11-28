# INTEGRATED — legacy corpora tree

The historical `raksha-code/corpora/` implementation moved here. The one
deterministic corpus generator is `evals/corpus.py`. A thin compatibility shim
at `raksha-code/corpora/` keeps historical imports working without duplicating
the implementation. Archived path constants were adjusted only so the repo root
still resolves after the move. See [`../INTEGRATED.md`](../INTEGRATED.md).

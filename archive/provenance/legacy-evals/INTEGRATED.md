# INTEGRATED — legacy eval tree

The historical `raksha-code/evals/` implementation moved here. The canonical
runner, generator, corpus and claims ledger are the root `evals/` package.
Compatibility wrappers remain at `raksha-code/evals/` for historical commands;
the frozen `run_maya.py` asset deliberately stays at its original hash-pinned
path and is not part of `make eval`. See [`../INTEGRATED.md`](../INTEGRATED.md).

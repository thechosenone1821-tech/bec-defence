"""Part 4 Phase 4 — organ fixture corpora.

A corpus here is a JSON file of *labelled cases*. A case is not a recorded
sample; it is a seeded generator expression that the harness compiles and runs.
That choice is deliberate and it is the whole honesty argument of this phase:

*A hand-written sample is a sample written by the same person who wrote the
detector, using the same assumptions.* It would score near-perfectly and mean
nothing. A seeded expression at least fails the same way twice, and its
parameters are visible: when the report says "bot offset 3", a reader can ask
what happens at offset 1 without trusting me.

What this does NOT give: any evidence about real attackers. Every file in
``corpora/organs/`` carries ``"provenance": "synthetic"`` and the report refuses
to publish a rate unless that field is present.
"""

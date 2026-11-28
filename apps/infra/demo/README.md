# Fake-hospital Infra demo

`hospital.py` is a functional, deterministic attack exercise for a synthetic
organisation. It creates signed or deliberately invalid events and sends them
through the active detector, quarantining, campaign fusion, Governor,
append-only ledger and dry-run executor path. The UI calls the Infra-owned demo
API to start, step, play and reset the scenario.

`hospital_topology.json` describes fake hospital VLANs, hosts, services and
edges. Crown clinical assets are protected by construction; the planner cannot
cut them. The exercise performs no real network action, uses no patient data,
invokes no Commander model and makes no real-world efficacy claim.

Open `/demo/hospital` on the Infra app. The read-only console also links to it.

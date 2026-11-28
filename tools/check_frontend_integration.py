#!/usr/bin/env python3
"""Gate: the Phosphor console is integrated with the active Python backends.

Static checks only — :mod:`tools.run_frontend_smoke` does the HTTP half. This
gate proves that the shipped frontend

* builds to a static export that *both* apps serve as their default UI,
* calls only endpoints that exist: every path it requests is either a real
  backend route or a documented gateway compatibility view,
* keeps its Red Team replay in sync with the detector registry's own firing
  fixtures, so the page cannot advertise a rule the detector would skip,
* holds no credentials and no browser-side signing — auth is injected by the
  same-origin Python gateway, with a timeout and an error envelope,
* carries none of the retired scorer-prototype code or the Next.js API
  prototypes from the uploaded bundle — the authoritative identifier list is
  imported from :mod:`tools.check_code_purge` rather than repeated here, and
* is wired into ``make`` and CI with the legacy surfaces still recoverable from
  ``archive/frontend-backup``.

Exit code 0 means every claim below held.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
FRONTEND = ROOT / "frontend"
STATIC = ROOT / "packages" / "frontend" / "static"
GATEWAY = ROOT / "packages" / "frontend" / "gateway.py"
BACKUP_DIR = ROOT / "archive" / "frontend-backup"

FRONTEND_CONTRACT = "raksha-phosphor-frontend-v1"
CONSOLE_ROUTES = (
    "attack-lab",
    "call-screen",
    "citizen-spine",
    "governance",
    "message-guard",
    "red-team",
    "rings",
    "vigil",
)
class Checker:
    def __init__(self) -> None:
        self.problems: list[str] = []

    def require(self, condition: bool, message: str) -> bool:
        if not condition:
            self.problems.append(message)
        return bool(condition)

    def text(self, path: pathlib.Path) -> str:
        if path.is_dir():
            self.problems.append(f"expected a file but found a directory: {path.relative_to(ROOT)}")
            return ""
        if not path.is_file():
            self.problems.append(f"missing file: {path.relative_to(ROOT)}")
            return ""
        return path.read_text(encoding="utf-8")

    def sources(self, base: pathlib.Path) -> str:
        """One blob of every source file under ``base`` (for call scanning)."""
        if not base.is_dir():
            self.problems.append(f"missing source tree: {base.relative_to(ROOT)}")
            return ""
        return "\n".join(path.read_text(encoding="utf-8") for path in _source_files(base))


def _source_files(base: pathlib.Path):
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".mjs", ".css", ".html"}:
            yield path


def _frontend_calls(source: str) -> set[tuple[str, str]]:
    """(surface, path) for every backend call the console makes.

    ``citizen()``/``spine()`` take a backend-relative path and the client
    prefixes ``/api/gateway/citizen`` or ``/api/gateway/spine``; the gate checks
    the pair, because a path the gateway merely proxies still has to exist.
    """
    calls: set[tuple[str, str]] = set()
    patterns = (
        ("citizen", r"""\bcitizen(?:<[^>]*>)?\(\s*[`"]([^`"]+)[`"]"""),
        ("spine", r"""\bspine(?:<[^>]*>)?\(\s*[`"]([^`"]+)[`"]"""),
        ("gateway", r"""\bfetch\(\s*[`"](/api/gateway[^`"]*)[`"]"""),
    )
    for kind, pattern in patterns:
        for match in re.finditer(pattern, source):
            calls.add((kind, match.group(1).strip()))
    if re.search(r"\bspineSigned(?:<[^>]*>)?\(", source):
        calls.add(("gateway", "/api/gateway/spine-signed"))
    if re.search(r"\bgatewayStatus(?:<[^>]*>)?\(", source):
        calls.add(("gateway", "/api/gateway/status"))
    return calls


def check_package_manifest(ck: Checker) -> None:
    raw = ck.text(FRONTEND / "package.json")
    if not raw:
        return
    pkg = json.loads(raw)
    ck.require(pkg.get("name") == "raksha-phosphor-frontend",
               "frontend/package.json is not the raksha-phosphor-frontend package")
    scripts = pkg.get("scripts", {})
    ck.require(scripts.get("build") == "next build && node scripts/sync-static.mjs",
               "frontend build script must export statically and sync packages/frontend/static")
    ck.require("next dev -H 0.0.0.0" in scripts.get("dev", ""),
               "frontend dev server must bind all interfaces for the preview")
    ck.require(scripts.get("typecheck") == "tsc --noEmit",
               "frontend must keep an explicit typecheck script")
    ck.require(all("bun" not in command.lower() for command in scripts.values()),
               "frontend scripts still invoke Bun, which is not the repository toolchain")
    ck.require(not any(key.startswith("db:") for key in scripts),
               "frontend still carries the Prisma database scripts")

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for banned in ("prisma", "@prisma/client", "bun-types", "z-ai-web-dev-sdk",
                   "next-auth", "zod", "@tanstack/react-query", "bcryptjs"):
        ck.require(banned not in deps,
                   f"frontend declares the unused/retired dependency {banned}")
    ck.require("@types/node" in pkg.get("devDependencies", {}),
               "frontend must pin @types/node so npm ci + tsc --noEmit stay reproducible")
    for name in ("next", "react", "react-dom", "typescript", "tailwindcss"):
        ck.require(name in deps, f"frontend lost the required dependency {name}")

    ck.require((FRONTEND / "package-lock.json").is_file(),
               "frontend/package-lock.json is missing, so `npm ci` cannot be reproducible")
    ck.require(not (FRONTEND / "bun.lock").exists(),
               "frontend/bun.lock is still present alongside package-lock.json")
    lock_raw = ck.text(FRONTEND / "package-lock.json")
    if lock_raw:
        lock = json.loads(lock_raw)
        root_pkg = lock.get("packages", {}).get("", {})
        ck.require(root_pkg.get("dependencies") == pkg.get("dependencies"),
                   "frontend/package-lock.json dependencies are out of sync with package.json")
        ck.require(root_pkg.get("devDependencies") == pkg.get("devDependencies"),
                   "frontend/package-lock.json devDependencies are out of sync with package.json")


def check_next_config(ck: Checker) -> None:
    source = ck.text(FRONTEND / "next.config.ts")
    if not source:
        return
    ck.require('output: "export"' in source, "frontend must export a static bundle")
    ck.require('trailingSlash: true' in source,
               "static export needs trailingSlash so directory index.html files resolve")
    ck.require("ignoreBuildErrors" not in source,
               "frontend build must not skip TypeScript validation")
    ck.require(not re.search(r"^\s*eslint\s*:", source, re.M),
               "next.config.ts must not carry the removed Next 16 `eslint` key")


def check_routes_and_static_build(ck: Checker) -> None:
    apps_source = ck.text(FRONTEND / "src" / "lib" / "apps.ts")
    routes = set(re.findall(r"""route:\s*"/console/([^"]+)\"""", apps_source))
    ids = set(re.findall(r"""^\s*id:\s*"([^"]+)",""", apps_source, re.M))
    ck.require(routes == set(CONSOLE_ROUTES),
               f"console routes drifted from the shipped set: {sorted(routes)}")
    ck.require(ids == set(CONSOLE_ROUTES),
               f"subapplication ids drifted from the shipped set: {sorted(ids)}")
    for route in CONSOLE_ROUTES:
        page = FRONTEND / "src" / "app" / "console" / route / "page.tsx"
        ck.require(page.is_file(), f"missing page module for /console/{route}")
        ck.require((STATIC / "console" / route / "index.html").is_file(),
                   f"static build is missing /console/{route}/ — run `make frontend-build`")
    ck.require((STATIC / "index.html").is_file(),
               "static build is missing its landing page — run `make frontend-build`")
    ck.require((STATIC / "_next" / "static").is_dir(),
               "static build is missing its _next/static chunks")
    index = ck.text(STATIC / "index.html")
    ck.require("ARK OMNITEK" in index, "static landing page lost the ARK OMNITEK title")
    # the committed bundle is what the apps serve, so it must be exactly what the
    # build produces — a hand-edited or forgotten rebuild shows up here
    export = FRONTEND / "out"
    if export.is_dir():
        import hashlib

        def digest(root: pathlib.Path) -> dict[str, str]:
            return {
                str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted(root.rglob("*")) if f.is_file()
            }

        built, committed = digest(export), digest(STATIC)
        ck.require(built == committed,
                   "packages/frontend/static is not the current build — run `make frontend-build`"
                   f" (differs: {sorted(set(built.items()) ^ set(committed.items()))[:3]})")


def check_backend_endpoints(ck: Checker) -> None:
    """Every path the console asks for must exist on the backend it names."""
    from apps.infra import features as infra_features  # local import: constants only

    infra_text = ck.text(ROOT / "apps" / "infra" / "backend" / "app.py")
    runtime_text = ck.text(ROOT / "packages" / "spine" / "runtime.py")
    citizen_text = ck.text(ROOT / "apps" / "citizen" / "api.py")
    gateway_text = ck.text(GATEWAY)

    from apps.citizen import features as citizen_features  # constants only

    def resolve(token: str) -> str:
        for module in (infra_features, citizen_features):
            value = getattr(module, token, "")
            if value:
                return str(value)
        return ""

    def routes(text: str) -> set[str]:
        paths: set[str] = set()
        for match in re.finditer(
            r"""@app\.(?:get|post|put|patch|delete|api_route|websocket)\(\s*([^)\n]+)""",
            text,
        ):
            for decl in re.finditer(r'"/[^"]*"|(?:infra_features|features)\.([A-Za-z_]+)', match.group(1)):
                token = decl.group(0)
                paths.add(token.strip('"') if token.startswith('"') else resolve(decl.group(1)))
        return {p for p in paths if p}

    infra_routes = routes(infra_text) | routes(runtime_text)
    citizen_routes = routes(citizen_text)
    compat = set(re.findall(r'sub_path == "([^"]+)"', gateway_text)) | set(
        re.findall(r'sub_path\.startswith\("([^"]+)"\)', gateway_text)
    )

    for kind, path in sorted(_frontend_calls(ck.sources(FRONTEND / "src"))):
        template = "${" in path
        clean = path.split("${")[0].rstrip("/")
        if kind == "gateway":
            if clean.startswith("/api/gateway/spine/"):
                kind, clean = "spine", clean[len("/api/gateway/spine/"):]
            elif clean.startswith("/api/gateway/citizen/"):
                kind, clean = "citizen", clean[len("/api/gateway/citizen/"):]
        if kind == "gateway":
            ok = clean in ("/api/gateway/spine-signed", "/api/gateway/status")
            ck.require(ok, f"the console asks the gateway for an unhandled path: {path}")
            continue
        if kind == "citizen":
            sub = clean.lstrip("/")
            ok = (f"/{sub}" in citizen_routes or sub in compat
                  or (template and any(r.startswith(f"/{sub}") for r in citizen_routes)))
            ck.require(ok, f"citizen path /{sub} is not served by apps/citizen/api.py")
            continue
        sub = clean.lstrip("/")
        ok = (f"/{sub}" in infra_routes or sub in compat
              or (template and any(r.startswith(f"/{sub}") for r in infra_routes)))
        ck.require(ok, f"spine path /{sub} is neither an Infra route nor a gateway compatibility view")

    # the gateway must not invent backend endpoints for its health probes
    for probe in re.findall(r'_target_url\((?:citizen|infra)_url\(\), "([^"]+)"\)', gateway_text):
        source = citizen_text if "citizen" in probe else infra_text + runtime_text
        ck.require(probe in source, f"gateway probes {probe}, which no active backend serves")

    # compat views have to say what they are, and stay read-only
    for view in ("_state_view", "_orchestrate_compat", "_containment_compat", "_fleet_compat"):
        ck.require(view in gateway_text, f"gateway lost its {view} compatibility view")
    ck.require(gateway_text.count("VIEW_LABEL") >= 4,
               "gateway compatibility views must each label themselves as a view")
    ck.require('"live_control": False' in gateway_text,
               "gateway fleet view must report that live organ control is not wired")
    ck.require('"real_action_count": 0' in gateway_text,
               "gateway containment view must report zero real actions")
    for banned in ("planes_3_4", "GUARDED_AUTO", '"all_healthy": True', '"state": "HEALTHY"'):
        ck.require(banned not in gateway_text,
                   f"gateway fabricates backend state with {banned}")


def check_auth_and_errors(ck: Checker) -> None:
    client = ck.text(FRONTEND / "src" / "lib" / "gateway.ts")
    gateway_text = ck.text(GATEWAY)
    ck.require("AbortController" in client and "timeoutMs" in client,
               "the gateway client must time out instead of hanging a console panel")
    ck.require('"X-Gateway-Client"' in client,
               "the gateway client should identify itself for request tracing")
    ck.require('cache: "no-store"' in client,
               "backend reads must not be cached by the browser")
    for secret in ("X-API-Token", "Bearer ", "demo-observer-token", "demo-sensor-token",
                   "raksha-phase678", "localStorage.setItem(\"token"):
        hits = [str(p.relative_to(FRONTEND)) for p in _source_files(FRONTEND / "src")
                if secret in p.read_text(encoding="utf-8")]
        ck.require(not hits, f"credential material {secret!r} leaked into the browser bundle: {hits}")
    ck.require('"X-API-Token": token' in gateway_text or 'headers["X-API-Token"] = token' in gateway_text,
               "the gateway must inject the scoped token server-side")
    ck.require("read_token()" in gateway_text and "sensor_token()" in gateway_text,
               "the gateway must resolve both the read and the ingest credential")
    env_text = ck.text(FRONTEND / ".env.example")
    for name in ("RAKSHA_CITIZEN_INTERNAL_URL", "RAKSHA_INFRA_INTERNAL_URL",
                 "RAKSHA_FRONTEND_READ_TOKEN", "RAKSHA_FRONTEND_SENSOR_TOKEN"):
        ck.require(name in env_text, f"frontend/.env.example must document {name}")
    for stale in ("DATABASE_URL", "SPINE_BUS_KEY", "NEXT_PUBLIC_SPINE_WS_URL", "CITIZEN_API_URL"):
        ck.require(stale not in env_text, f"frontend/.env.example still advertises {stale}")
    ck.require("SPINE_BUS_KEY" not in gateway_text,
               "the gateway must sign with the ingest key, not the retired bus key")


def check_retired_surfaces(ck: Checker) -> None:
    """The uploaded bundle shipped a retired prototype; none of it may survive.

    The identifier vocabulary is owned by ``tools/check_code_purge.py`` and is
    imported here instead of being copied, so the two gates cannot drift.
    """
    from tools.check_code_purge import RETIRED_CONTENT, RETIRED_NAME  # noqa: PLC0415

    for path in (FRONTEND / "src" / "app" / "api", FRONTEND / "prisma",
                 FRONTEND / "tailwind.config.ts", FRONTEND / "bun.lock"):
        ck.require(not path.exists(),
                   f"retired prototype path is still active: {path.relative_to(ROOT)}")
    # allow-lists, so no retired module can come back under any name
    lib_modules = sorted(x.name for x in (FRONTEND / "src" / "lib").glob("*.ts"))
    ck.require(lib_modules == ["apps.ts", "gateway.ts", "mode-store.ts",
                              "scenarios.ts", "session-signals.ts", "utils.ts"],
               f"frontend/src/lib module set changed: {lib_modules}")
    features = sorted(x.stem for x in (FRONTEND / "src" / "components" / "features").glob("*.tsx"))
    ck.require(features == sorted(CONSOLE_ROUTES),
               f"frontend feature modules are not exactly the console routes: {features}")
    hooks = sorted(x.name for x in (FRONTEND / "src" / "hooks").glob("*.ts"))
    ck.require(hooks == ["use-mobile.ts", "use-poll.ts", "use-spine-feed.ts", "use-toast.ts"],
               f"frontend hook module set changed: {hooks}")
    banned = re.compile(
        r"""getUserMedia|MediaRecorder|AudioWorklet|audio\.(?:createContext|getUserMedia)|"""
        r"""new WebSocket|next/font/google|z-ai-web-dev-sdk|\bprisma\b""",
        re.I,
    )
    retired = tuple(RETIRED_CONTENT) + (RETIRED_NAME,)
    for path in _source_files(FRONTEND / "src"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if banned.search(line) or any(pattern.search(line) for pattern in retired):
                ck.problems.append(
                    f"retired capability in {path.relative_to(FRONTEND)}:{lineno}: {line.strip()[:90]}"
                )
    for path in _source_files(FRONTEND / "src"):
        text = path.read_text(encoding="utf-8")
        for match in re.findall(r"""fetch\(\s*["'](https?://[^"']+|//[^"']+)""", text):
            ck.problems.append(f"cross-origin fetch in {path.relative_to(FRONTEND)}: {match}")


def check_static_bundle_is_self_contained(ck: Checker) -> None:
    allowed = (
        "http://www.w3.org",          # svg/xml namespaces
        "https://react.dev",          # licence comments in vendored chunks
        "http://localhost",           # README-style text inside source maps
    )
    offenders: list[str] = []
    for path in _source_files(STATIC):
        text = path.read_text(encoding="utf-8", errors="replace")
        for url in re.findall(r"""(?:src|href)="(https?://[^"]+)\"""", text):
            if not url.startswith(allowed):
                offenders.append(f"{path.relative_to(STATIC)}: {url}")
        if path.suffix in {".css", ".html"}:
            for url in re.findall(r"""https?://[a-z0-9.-]+\.[a-z]{2,}[^"'\s)]*""", text):
                if not url.startswith(allowed):
                    offenders.append(f"{path.relative_to(STATIC)}: {url}")
    ck.require(not offenders, f"static bundle reaches out to the network: {offenders[:6]}")
    ck.require(not list(STATIC.rglob("*.map")), "static bundle should not ship source maps")


def check_app_registration(ck: Checker) -> None:
    citizen = ck.text(ROOT / "apps" / "citizen" / "api.py")
    infra = ck.text(ROOT / "apps" / "infra" / "backend" / "app.py")
    ck.require('register_frontend(app, service="citizen", root_redirect="/console/call-screen")' in citizen,
               "the Citizen app must serve the Phosphor console at /console/call-screen")
    ck.require('register_frontend(app, service="infra", root_redirect="/console/rings")' in infra,
               "the Infra app must serve the Phosphor console at /console/rings")
    for app_dir, redirect in (("citizen", "/console/call-screen"), ("infra", "/console/rings")):
        manifest = json.loads(ck.text(ROOT / "apps" / app_dir / "BOOT_MANIFEST.json") or "{}")
        ck.require(manifest.get("frontend_contract") == FRONTEND_CONTRACT,
                   f"apps/{app_dir} boot manifest does not pin the frontend contract")
        ck.require(manifest.get("root_redirect") == redirect,
                   f"apps/{app_dir} root redirect must land on the Phosphor console ({redirect})")
        ck.require(manifest.get("frontend_health_path") == "/api/frontend/health",
                   f"apps/{app_dir} boot manifest must publish /api/frontend/health")
        target = STATIC / redirect.strip("/") / "index.html"
        ck.require(target.is_file(), f"root redirect target is not built: {target.relative_to(ROOT)}")
    launcher = ck.text(ROOT / "tools" / "launch_apps.py")
    for name in ("RAKSHA_CITIZEN_INTERNAL_URL", "RAKSHA_INFRA_INTERNAL_URL",
                 "RAKSHA_FRONTEND_READ_TOKEN", "RAKSHA_BUS_URL", "RAKSHA_SENSOR_TOKEN"):
        ck.require(name in launcher, f"tools/launch_apps.py must wire {name} for the gateway")


def check_red_team_matches_registry(ck: Checker) -> None:
    """The replay page may only use fixtures the active detector really fires on."""
    from apps.infra.detectors.registry import ORGAN_SPECS  # noqa: PLC0415

    firing = {spec.name: dict(spec.firing_payload) for spec in ORGAN_SPECS}
    source = ck.text(FRONTEND / "src" / "components" / "features" / "red-team.tsx")
    steps = re.findall(
        r"""organ:\s*"([a-z_]+)",.*?leg:\s*"(citizen|infra)",.*?severity:\s*(\d+),.*?"""
        r"""payload:\s*\{([^}]*)\}""",
        source,
        re.S,
    )
    ck.require(len(steps) == 5, f"Red Team replay must replay 5 registry techniques, found {len(steps)}")
    numbers = re.compile(r"""([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(-?\d+(?:\.\d+)?)""")
    for organ, leg, severity, payload in steps:
        ck.require(organ in firing, f"Red Team uses the unknown organ {organ!r}")
        if organ not in firing:
            continue
        claimed = {key: float(value) for key, value in numbers.findall(payload)}
        expected = {key: float(value) for key, value in firing[organ].items()}
        ck.require(claimed == expected,
                   f"Red Team payload for {organ} is {claimed}, registry fires on {expected}")
        ck.require(leg in {"citizen", "infra"} and 1 <= int(severity) <= 5,
                   f"Red Team step on {organ} has an invalid leg/severity")
    legs = {leg for _, leg, _, _ in steps}
    ck.require(legs == {"citizen", "infra"},
               "Red Team replay needs findings on both legs or the campaign cannot fuse")
    ck.require('"/api/gateway/spine-signed"' in ck.text(FRONTEND / "src" / "lib" / "gateway.ts"),
               "signed replay events must be minted by the gateway, never in the browser")


def check_attack_lab_matches_scenarios(ck: Checker) -> None:
    """The Attack Lab may only script events the detector answers as claimed.

    The page reads its script from the Infra app instead of copying fixtures, which
    is the whole point of the module split: this gate then proves the script itself
    is honest, one ``detect(event)`` call per step, and that every generated id and
    summary carries the SIMULATED label with a per-run tag so a repeat cannot reuse
    an ``event_id`` the runtime would refuse.
    """
    from apps.infra import features as infra_features  # noqa: PLC0415
    from apps.infra.demo.scenarios import SCENARIOS, catalogue_snapshot  # noqa: PLC0415
    from apps.infra.detectors.registry import ORGAN_FIXTURES, detect  # noqa: PLC0415
    from packages.contracts.envelope import ingest_key, sign_event  # noqa: PLC0415

    snapshot = catalogue_snapshot()
    ck.require(snapshot["contract"] == infra_features.SCENARIOS_CONTRACT
               and snapshot["status"] == "ok",
               "the scenario catalogue and apps/infra/features.py disagree on the contract")
    ck.require(snapshot["simulated"] is True and snapshot["attack_executed"] is False
               and snapshot["dry_run"] is True and snapshot["live_action_paths"] == 0
               and snapshot["model_backed"] is False and snapshot["commander_enabled"] is False,
               "the scenario catalogue does not declare itself simulated, dry-run and non-attacking")
    card = infra_features.attack_scenarios_card()
    ck.require(card["catalogue_path"] == infra_features.SCENARIOS_PATH
               and card["scenario_count"] == len(SCENARIOS)
               and card["step_count"] == snapshot["totals"]["steps"]
               and card["real_action_count"] == 0,
               "the Attack Lab capability card no longer describes the catalogue")
    ck.require("simulated_attack_scenarios" in infra_features.FEATURE_FLAGS,
               "the Attack Lab capability flag is not registered")
    ck.require(f'"{infra_features.SCENARIOS_PATH}"' in ck.text(ROOT / "apps" / "infra" / "BOOT_MANIFEST.json"),
               "the Infra boot manifest does not record the scenario catalogue path")
    # every organ in the registry must be demonstrable, and each step must answer
    # exactly as its own script claims
    scripted_organs = {str(step["organ"]) for sc in snapshot["scenarios"] for step in sc["steps"]}
    ck.require(scripted_organs == set(ORGAN_FIXTURES),
               f"the Attack Lab covers {sorted(scripted_organs)}, registry organs are {sorted(ORGAN_FIXTURES)}")
    key = ingest_key()
    for scenario in snapshot["scenarios"]:
        for step in scenario["steps"]:
            label = f"{scenario['id']}/{step['key']}"
            event = dict(step["event"])
            ck.require(str(event["summary"]).startswith(f"{snapshot['label']} \u00b7 "),
                       f"{label} is not labelled SIMULATED in the event the console posts")
            ck.require(all("{tag}" in str(event[field]) for field in ("event_id", "campaign_id", "case_id"))
                       and "{ts}" in str(event["ts"]),
                       f"{label} has no per-run tag, so a repeat would reuse an event id")
            ck.require(set(event["payload"]) <= set(ORGAN_FIXTURES[step["organ"]][step["fixture"]]),
                       f"{label} sends features the registry fixture for {step['fixture']} does not define")
            if step["envelope"] == "signed":
                event = sign_event(event, key)
            result = detect(event, key=key)
            rule = str((result.finding or {}).get("rule_id") or "")
            if step["expects"] == "finding":
                ok = result.status == "finding" and rule == step["expects_rule"]
            elif step["expects"] == "no_detection":
                ok = result.status == "no_detection"
            else:
                ok = result.status == "quarantined"
            ck.require(ok, f"{label} claims {step['expects']} ({step['expects_rule'] or 'no rule'}) "
                           f"but detect() says {result.status} {rule or result.reason}".rstrip())
    # and the page must drive that catalogue, not a second copy of it
    lib = ck.text(FRONTEND / "src" / "lib" / "scenarios.ts")
    feature = ck.text(FRONTEND / "src" / "components" / "features" / "attack-lab.tsx")
    ck.require(f'spine<ScenarioCatalogue>("{infra_features.SCENARIOS_PATH}")' in lib,
               "the Attack Lab client must read its script from the Infra catalogue route")
    ck.require(f'SCENARIO_CATALOGUE_PATH = "{infra_features.SCENARIOS_PATH}"' in lib,
               "the Attack Lab client's exported path constant must match apps/infra/features.py")
    ck.require("runScenario" in lib and "spineSigned" in lib and '"/api/ingest"' in lib,
               "the Attack Lab must ingest signed events through the gateway and untrusted ones as sent")
    ck.require("newRunTag" in lib, "the Attack Lab must mint a fresh run tag so repeats stay valid")
    ck.require("loadCatalogue" in feature and "runScenario" in feature,
               "the Attack Lab page must render the served catalogue, not a copied script")
    ck.require('"@/lib/scenarios"' in feature and "/api/state" in feature,
               "the Attack Lab dashboard must read the runtime's own state view")
    ck.require("SIMULATED_LABEL" in feature and "Reset" in feature
               and re.search(r"const reset\b|function reset\b", feature) is not None,
               "the Attack Lab must label its rows SIMULATED and offer a reset")
    ck.require("ALERT ·" in feature,
               "the Attack Lab must raise a visible alert for the steps the runtime flagged")
    ck.require("severityVar" in feature and "simEventPrefix" in feature,
               "the Attack Lab must tint rows by the event's own severity and know its own run ids")
    # the timeline is per step, per run, and each row keeps the runtime's own
    # verdict next to the script's expectation — that is what makes drift visible
    for payload in ("StepOutcome", "STATUS_META", "asExpected", "outcomes", "runScenario"):
        ck.require(payload in feature, f"the Attack Lab timeline lost {payload}")
    ck.require("outcomes: StepOutcome[]" in ck.text(FRONTEND / "src" / "lib" / "scenarios.ts")
               or "outcomes: StepOutcome[]" in feature,
               "each scenario run must keep one outcome row per scripted step")
    ck.require("ledger" in feature and "seq" in feature,
               "the Attack Lab timeline must show each event's ledger sequence")
    for banned in ("localStorage", "sessionStorage", "setTimeout(() => set"):
        ck.require(banned not in lib, f"the Attack Lab client must not persist or fake state ({banned})")


def check_gates_and_recovery(ck: Checker) -> None:
    makefile = ck.text(ROOT / "Makefile")
    for target in ("frontend-install:", "frontend-build:", "frontend-check:", "frontend-smoke:"):
        ck.require(target in makefile, f"Makefile lost the {target[:-1]} target")
    ck.require("npm ci" in makefile, "Makefile must install frontend dependencies with npm ci")
    ci = ck.text(ROOT / ".github" / "workflows" / "ci.yml")
    for step in ("npm ci", "npm run build", "tools/check_frontend_integration.py",
                 "tools/run_frontend_smoke.py"):
        ck.require(step in ci, f"CI no longer runs {step}")
    ignore = ck.text(ROOT / ".gitignore")
    for entry in ("frontend/node_modules/", "frontend/.next/", "frontend/out/"):
        ck.require(entry in ignore, f".gitignore must keep {entry} out of the release")
    ck.require((ROOT / "ark-omnitek-frontend.zip").is_file(),
               "the uploaded frontend bundle must stay recoverable in the repository")
    archive = BACKUP_DIR / "legacy-frontends-20261126.tar.gz"
    checksum = BACKUP_DIR / "legacy-frontends-20261126.sha256"
    ck.require(archive.is_file() and checksum.is_file(),
               "the pre-replacement backup of the legacy frontends must stay available")


def main() -> int:
    ck = Checker()
    check_package_manifest(ck)
    check_next_config(ck)
    check_routes_and_static_build(ck)
    check_backend_endpoints(ck)
    check_auth_and_errors(ck)
    check_retired_surfaces(ck)
    check_static_bundle_is_self_contained(ck)
    check_app_registration(ck)
    check_red_team_matches_registry(ck)
    check_attack_lab_matches_scenarios(ck)
    check_gates_and_recovery(ck)
    if ck.problems:
        for problem in ck.problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        print(f"FAIL: {len(ck.problems)} Phosphor frontend integration problem(s)", file=sys.stderr)
        return 1
    routes = ", ".join(f"/console/{name}" for name in CONSOLE_ROUTES)
    print(f"OK: Phosphor frontend integrated — static export serves {routes} from both apps, "
          "gateway paths resolve to active Citizen/Infra endpoints, auth stays server-side, "
          "replay fixtures and the Attack Lab script match the detector registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

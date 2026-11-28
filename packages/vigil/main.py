# packages/vigil/main.py
"""VIGIL route adapter for the existing Citizen FastAPI app.

The uploaded engine is a shared package, not a third bootable service. This
module exposes an ``APIRouter`` prefixed with ``/vigil`` and a ``mount_vigil``
helper that Citizen calls while building its one service. Static assets and API
routes are same-origin under that prefix; the browser uses relative URLs.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from packages.vigil.config import EVALUATION_TEST_REGISTRY, HARDWARE_CONFIG, PROTECTION_POLICIES
from packages.vigil.engines.evaluation_engine import EVALUATION_ENGINE
from packages.vigil.engines.security_engine import SECURITY_ENGINE
from packages.vigil.engines.vigil_core import VIGIL_CORE, ImageValidationError
from packages.vigil.models.privacy_net import MODEL_MANAGER
from packages.vigil.schemas import ManualRegionInput, TransformRequest

STATIC_DIR = Path(__file__).resolve().parent / "static"
VIGIL_PREFIX = "/vigil"

router = APIRouter(prefix=VIGIL_PREFIX, tags=["vigil"])


class RegionUpdatePayload(BaseModel):
    active_region_ids: List[str] = Field(default_factory=list)
    excluded_region_ids: List[str] = Field(default_factory=list)
    manual_regions: List[ManualRegionInput] = Field(default_factory=list)


async def handle_validation_error(_: Request, exc: ImageValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "IMAGE_VALIDATION_ERROR", "detail": str(exc)})


@router.get("/", include_in_schema=False)
async def serve_dashboard() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(str(index_path))


@router.get("/api/overview")
async def get_overview() -> Dict[str, Any]:
    """Returns system status, model mode, hardware caps and recent sessions."""
    return VIGIL_CORE.get_system_overview()


@router.get("/api/policies")
async def get_policies() -> Dict[str, Any]:
    """Returns configurable protection policies and the evaluation test registry."""
    return {
        "policies": {k: vars(v) for k, v in PROTECTION_POLICIES.items()},
        "evaluation_test_registry": EVALUATION_TEST_REGISTRY,
    }


@router.post("/api/sessions/upload")
async def upload_and_analyze_image(
    file: UploadFile = File(...),
    auto_resize: bool = Form(True),
) -> Dict[str, Any]:
    """Workflow Steps 1-3: upload, validate, run PerceptionEngine, return regions + previews."""
    try:
        raw_bytes = await file.read()
        if len(raw_bytes) > HARDWARE_CONFIG.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {HARDWARE_CONFIG.max_upload_bytes // (1024 * 1024)} MB limit.",
            )
        return VIGIL_CORE.ingest_and_analyze(
            raw_bytes=raw_bytes,
            filename=file.filename or "upload.png",
            auto_resize=auto_resize,
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyse image: {exc}") from exc
    finally:
        gc.collect()


@router.put("/api/sessions/{session_id}/regions")
async def update_regions(session_id: str, payload: RegionUpdatePayload) -> Dict[str, Any]:
    """Workflow Step 4: update active/excluded regions and persist manual boxes."""
    session = SECURITY_ENGINE.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired.")
    updated = VIGIL_CORE.update_session_regions(
        session=session,
        active_region_ids=payload.active_region_ids,
        excluded_region_ids=payload.excluded_region_ids,
        manual_regions=payload.manual_regions,
    )
    return {
        "session_id": session_id,
        "regions": [r.model_dump() for r in updated],
        "active_count": sum(1 for r in updated if r.active),
        "excluded_count": sum(1 for r in updated if not r.active),
    }


@router.post("/api/vigil/execute")
async def execute_vigil(request: TransformRequest) -> Dict[str, Any]:
    """Workflow Steps 5-9: execute configured VIGIL pipeline, evaluate, audit, sanitize PNG."""
    session = SECURITY_ENGINE.get_session(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{request.session_id}' not found or expired. Please re-upload the image.",
        )
    try:
        return VIGIL_CORE.execute_vigil_pipeline(
            session=session,
            config=request.config,
            run_evaluation=request.run_evaluation,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"VIGIL execution error: {exc}") from exc
    finally:
        gc.collect()


@router.post("/api/vigil/evaluate/{session_id}")
async def run_standalone_evaluation(session_id: str) -> Dict[str, Any]:
    """Re-runs the VIGIL Evaluation Engine on an already-transformed session."""
    session = SECURITY_ENGINE.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired.")
    if session.transformed_rgb is None or session.protection_mask is None or session.last_config is None:
        raise HTTPException(
            status_code=400,
            detail="Execute a VIGIL transformation on this session before running evaluation.",
        )
    eval_report = EVALUATION_ENGINE.evaluate(
        original_rgb=session.original_rgb,
        transformed_rgb=session.transformed_rgb,
        target_mask=session.protection_mask,
        resolved_regions=session.regions,
        config=session.last_config,
    )
    session.last_evaluation = eval_report
    if session.last_audit is not None:
        session.last_audit.evaluation_summary = eval_report
    SECURITY_ENGINE.update_summary(session)
    return {"session_id": session_id, "evaluation_report": eval_report.model_dump()}


@router.post("/api/security/verify-png")
async def verify_uploaded_png(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Standalone binary PNG chunk & CRC32 verifier for inspecting exported files."""
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return SECURITY_ENGINE.verify_png_bytes(raw_bytes).model_dump()


@router.get("/api/export/{session_id}/image.png")
async def export_sanitized_png(session_id: str) -> Response:
    """Workflow Step 10a: download the metadata-sanitized transformed PNG."""
    session = SECURITY_ENGINE.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired.")
    if session.sanitized_png_bytes is None:
        raise HTTPException(status_code=400, detail="No transformed image available. Execute VIGIL first.")
    return Response(
        content=session.sanitized_png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="vigil_{session_id}.png"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/export/{session_id}/audit.json")
async def export_audit_json(session_id: str) -> Response:
    """Workflow Step 10b: download the machine-readable JSON audit & evaluation report."""
    session = SECURITY_ENGINE.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired.")
    if session.last_audit is None:
        raise HTTPException(status_code=400, detail="No audit report available. Execute VIGIL first.")
    payload = json.dumps(session.last_audit.model_dump(), indent=2, default=str).encode("utf-8")
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="vigil_audit_{session_id}.json"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/export/{session_id}/bundle.zip")
async def export_zip_bundle(session_id: str) -> Response:
    """Workflow Step 10c: download the complete ZIP bundle (PNG + JSON + Manifest + History)."""
    session = SECURITY_ENGINE.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired.")
    try:
        zip_bytes = VIGIL_CORE.build_export_zip(session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="VIGIL_Bundle_{session_id}.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Explicitly purges a session's pixel buffers from RAM."""
    removed = SECURITY_ENGINE.delete_session(session_id)
    return {"session_id": session_id, "purged": removed}


def mount_vigil(app: FastAPI) -> None:
    """Mount VIGIL into one of the two existing FastAPI services.

    No standalone ``FastAPI`` object is created here. The Citizen app owns the
    process, the exception handler, the static mount and the prefixed routes.
    """
    app.include_router(router)
    app.add_exception_handler(ImageValidationError, handle_validation_error)
    app.state.vigil_integrated = True
    app.state.vigil_prefix = VIGIL_PREFIX
    app.state.vigil_core = VIGIL_CORE
    if STATIC_DIR.exists():
        app.mount(
            f"{VIGIL_PREFIX}/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="vigil-static",
        )

    @app.get(VIGIL_PREFIX, include_in_schema=False)
    async def vigil_root_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{VIGIL_PREFIX}/", status_code=307)


__all__ = ["VIGIL_PREFIX", "router", "mount_vigil", "handle_validation_error"]

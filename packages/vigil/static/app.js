// packages/vigil/static/app.js
"use strict";

const VigilState = {
  sessionId: null,
  originalImageElement: null,
  workingWidth: 800,
  workingHeight: 500,
  regions: [],
  manualRegions: [],
  urls: {
    original: null,
    segmentation: null,
    transformed: null,
    mask: null,
    heatmap: null,
  },
  isDrawing: false,
  dragStart: { x: 0, y: 0 },
  dragCurrent: { x: 0, y: 0 },
};

const CATEGORY_COLORS = {
  face: "#2f81f7",
  qr_code: "#3fb950",
  licence_plate: "#d29922",
  text: "#a371f7",
  manual: "#f85149",
};

function showAlert(message) {
  const el = document.getElementById("global-alert");
  if (!message) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.textContent = message;
  el.classList.remove("hidden");
}

function switchView(viewId) {
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === viewId);
  });
  document.querySelectorAll(".nav-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-view") === viewId);
  });
  if (viewId === "view-detection") {
    renderDetectionCanvas();
  }
}

function markWorkflowStep(stepNum) {
  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById(`wf-${i}`);
    if (el && i <= stepNum) {
      el.classList.add("done");
    }
  }
}

function statusBadgeHtml(status) {
  const s = String(status || "PENDING").toUpperCase();
  if (s === "PASS" || s === "AVAILABLE" || s === "NEURAL_WEIGHTS_ACTIVE") {
    return `<span class="badge badge-pass">${s}</span>`;
  }
  if (s === "FAIL" || s === "UNAVAILABLE") {
    return `<span class="badge badge-fail">${s}</span>`;
  }
  return `<span class="badge badge-warn">${s}</span>`;
}

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ---------------------------------------------------------------------------
// 1. Overview & System Telemetry
// ---------------------------------------------------------------------------
async function refreshOverview() {
  try {
    const [ovRes, polRes] = await Promise.all([
      fetch("./api/overview"),
      fetch("./api/policies"),
    ]);
    if (!ovRes.ok) throw new Error(`Overview HTTP ${ovRes.status}`);
    if (!polRes.ok) throw new Error(`Policies HTTP ${polRes.status}`);

    const ov = await ovRes.json();
    const pol = await polRes.json();

    const modelStatus = ov["model_status"] || {};
    const hw = ov["hardware_profile"] || {};
    const sessInfo = ov["sessions"] || {};

    document.getElementById("hdr-model-mode").textContent = modelStatus["system_mode"] || "--";
    document.getElementById("hdr-cpu-threads").textContent = hw["cpu_threads_cap"] || "--";
    document.getElementById("hdr-rss-mb").textContent = hw["process_rss_mb"] || "--";

    document.getElementById("ov-system-mode").textContent = modelStatus["system_mode"] || "--";
    document.getElementById("ov-model-arch").textContent =
      `${modelStatus["architecture"] || "--"} (${modelStatus["weights_file"] || "--"})`;
    document.getElementById("ov-param-count").textContent =
      Number(modelStatus["parameter_count"] || 0).toLocaleString();
    document.getElementById("ov-cpu-profile").textContent = "Athlon 3000G Profile";
    document.getElementById("ov-dim-cap").textContent =
      `Max Dim: ${hw["max_image_dimension"]}px | Threads: ${hw["cpu_threads_cap"]}`;
    document.getElementById("ov-active-sessions").textContent =
      `${sessInfo["active_sessions_in_ram"] || 0} / ${sessInfo["max_active_sessions"] || 3}`;
    document.getElementById("ov-rss-detail").textContent =
      `Process RSS: ${hw["process_rss_mb"] || "--"} MB`;

    const banner = document.getElementById("fallback-banner");
    if (!modelStatus["is_neural_active"]) {
      banner.classList.remove("hidden");
      document.getElementById("fallback-banner-text").textContent =
        modelStatus["status_message"] || "FALLBACK MODE ACTIVE";
    } else {
      banner.classList.add("hidden");
    }

    // Recent sessions table
    const recent = sessInfo["recent_sessions"] || [];
    const tbody = document.getElementById("ov-sessions-tbody");
    if (recent.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="mono">No sessions recorded yet. Upload an image in Workspace.</td></tr>`;
    } else {
      tbody.innerHTML = recent
        .map((s) => `
          <tr>
            <td class="mono">${escapeHtml(s["session_id"])}</td>
            <td>${escapeHtml(s["filename"])}</td>
            <td class="mono">${escapeHtml(s["working_dimensions"])}</td>
            <td class="mono">${s["detected_regions_count"]}</td>
            <td class="mono">${escapeHtml(s["last_method"])}</td>
            <td class="mono">${s["full_image_ssim"] != null ? s["full_image_ssim"] : "--"}</td>
            <td>${statusBadgeHtml(s["audit_status"])}</td>
          </tr>`)
        .join("");
    }

    // Evaluation test registry
    const registry = pol["evaluation_test_registry"] || {};
    const regTbody = document.getElementById("ov-registry-tbody");
    regTbody.innerHTML = Object.entries(registry)
      .map(([key, info]) => `
        <tr>
          <td class="mono"><strong>${escapeHtml(key)}</strong></td>
          <td>${statusBadgeHtml(info["status"])}</td>
          <td>
            <div><strong>Scope:</strong> ${escapeHtml(info["scope"])}</div>
            <div style="color:var(--text-secondary); margin-top:2px;"><strong>Limitation:</strong> ${escapeHtml(info["limitation"])}</div>
          </td>
        </tr>`)
      .join("");
  } catch (err) {
    showAlert(`Failed to load system overview: ${err.message}`);
  }
}

// ---------------------------------------------------------------------------
// 2. Image Upload & Perception Analysis
// ---------------------------------------------------------------------------
async function handleUploadAndAnalyze() {
  showAlert(null);
  const fileInput = document.getElementById("file-upload-input");
  if (!fileInput.files || fileInput.files.length === 0) {
    showAlert("Please select an image file before clicking Upload & Analyse.");
    return;
  }

  const btn = document.getElementById("btn-upload-analyze");
  btn.disabled = true;
  btn.textContent = "Analysing Image...";

  try {
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("auto_resize", document.getElementById("chk-auto-resize").checked ? "true" : "false");

    const res = await fetch("./api/sessions/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data["detail"] || "Upload failed");
    }

    VigilState.sessionId = data["session_id"];
    VigilState.workingWidth = data["working_dimensions"]["width"];
    VigilState.workingHeight = data["working_dimensions"]["height"];
    VigilState.regions = data["regions"] || [];
    VigilState.manualRegions = [];
    VigilState.urls.original = data["original_preview_url"];
    VigilState.urls.segmentation = data["segmentation_overlay_url"];
    VigilState.urls.transformed = null;
    VigilState.urls.mask = null;
    VigilState.urls.heatmap = null;

    document.getElementById("hdr-session-id").textContent = VigilState.sessionId;
    document.getElementById("ws-orig-dims").textContent =
      `${VigilState.workingWidth}x${VigilState.workingHeight}` +
      (data["was_downscaled"] ? " (auto-resized)" : "");

    const origImg = document.getElementById("img-ws-original");
    origImg.src = VigilState.urls.original;
    origImg.classList.remove("hidden");
    document.getElementById("placeholder-ws-orig").classList.add("hidden");

    // Pre-populate output preview with 7-class segmentation overlay until VIGIL executes
    document.getElementById("sel-ws-view-mode").value = "segmentation";
    updateWorkspaceOutputViewport();

    // Load Image object for interactive Detection canvas
    const imgObj = new Image();
    imgObj.onload = () => {
      VigilState.originalImageElement = imgObj;
      renderDetectionCanvas();
    };
    imgObj.src = VigilState.urls.original;

    populateDetectionTable();
    updateRegionSummaryCounter();
    updateExportLinks();

    document.getElementById("btn-execute-vigil").disabled = false;
    markWorkflowStep(3);
    await refreshOverview();
  } catch (err) {
    showAlert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Upload & Analyse Image";
  }
}

function updateWorkspaceOutputViewport() {
  const mode = document.getElementById("sel-ws-view-mode").value;
  const outImg = document.getElementById("img-ws-output");
  const placeholder = document.getElementById("placeholder-ws-out");

  const targetUrl = VigilState.urls[mode] || VigilState.urls.transformed || VigilState.urls.segmentation;
  if (targetUrl) {
    outImg.src = targetUrl;
    outImg.classList.remove("hidden");
    placeholder.classList.add("hidden");
  } else {
    outImg.classList.add("hidden");
    placeholder.classList.remove("hidden");
  }
}

function updateRegionSummaryCounter() {
  const allRegs = [...VigilState.regions, ...VigilState.manualRegions];
  const activeCount = allRegs.filter((r) => r["active"]).length;
  document.getElementById("ws-region-summary").textContent =
    `${activeCount} active of ${allRegs.length} total regions`;
  const status = document.getElementById("det-canvas-status");
  if (status) status.textContent = `${allRegs.length} regions`;
}

// ---------------------------------------------------------------------------
// 3. Detection Canvas & Manual Region Correction
// ---------------------------------------------------------------------------
function populateDetectionTable() {
  const tbody = document.getElementById("det-regions-tbody");
  const allRegs = [...VigilState.regions, ...VigilState.manualRegions];

  if (allRegs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="mono">No regions detected. Draw a manual box on the canvas above if needed.</td></tr>`;
    return;
  }

  tbody.innerHTML = allRegs
    .map((r) => {
      const b = r["bbox"];
      const classes = (r["semantic_classes_present"] || []).join(", ") || "--";
      const checked = r["active"] ? "checked" : "";
      const color = CATEGORY_COLORS[r["category"]] || "#8b949e";
      return `
        <tr>
          <td><input type="checkbox" class="reg-toggle-chk" data-reg-id="${escapeHtml(r["region_id"])}" ${checked} /></td>
          <td class="mono">${escapeHtml(r["region_id"])}</td>
          <td><span class="badge" style="border-color:${color}; color:${color};">${escapeHtml(r["category"])}</span></td>
          <td class="mono">${b["x1"]}, ${b["y1"]}, ${b["x2"]}, ${b["y2"]}</td>
          <td class="mono">${Number(r["confidence"]).toFixed(2)}</td>
          <td class="mono">${escapeHtml(r["detector_source"])}</td>
          <td class="mono">${escapeHtml(classes)}</td>
        </tr>`;
    })
    .join("");

  document.querySelectorAll(".reg-toggle-chk").forEach((chk) => {
    chk.addEventListener("change", (ev) => {
      const regId = ev.target.getAttribute("data-reg-id");
      const target =
        VigilState.regions.find((r) => r["region_id"] === regId) ||
        VigilState.manualRegions.find((r) => r["region_id"] === regId);
      if (target) {
        target["active"] = ev.target.checked;
        renderDetectionCanvas();
        updateRegionSummaryCounter();
      }
    });
  });
}

function renderDetectionCanvas() {
  const canvas = document.getElementById("detection-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = VigilState.workingWidth || 800;
  canvas.height = VigilState.workingHeight || 500;

  ctx.fillStyle = "#07090c";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (VigilState.originalImageElement) {
    ctx.drawImage(VigilState.originalImageElement, 0, 0, canvas.width, canvas.height);
  }

  const allRegs = [...VigilState.regions, ...VigilState.manualRegions];
  allRegs.forEach((r) => {
    const b = r["bbox"];
    const w = b["x2"] - b["x1"];
    const h = b["y2"] - b["y1"];
    const color = CATEGORY_COLORS[r["category"]] || "#2f81f7";

    ctx.save();
    ctx.strokeStyle = r["active"] ? color : "#6e7681";
    ctx.lineWidth = r["active"] ? 2.5 : 1.5;
    if (!r["active"]) ctx.setLineDash([5, 4]);
    ctx.strokeRect(b["x1"], b["y1"], w, h);

    ctx.fillStyle = r["active"] ? color : "#484f58";
    const label = `[${r["category"]}] ${r["active"] ? "ACTIVE" : "EXCLUDED"}`;
    ctx.font = "11px SFMono-Regular, Consolas, monospace";
    const textWidth = ctx.measureText(label).width;
    ctx.fillRect(b["x1"], Math.max(0, b["y1"] - 18), textWidth + 8, 18);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, b["x1"] + 4, Math.max(12, b["y1"] - 5));
    ctx.restore();
  });

  if (VigilState.isDrawing) {
    const x1 = Math.min(VigilState.dragStart.x, VigilState.dragCurrent.x);
    const y1 = Math.min(VigilState.dragStart.y, VigilState.dragCurrent.y);
    const w = Math.abs(VigilState.dragCurrent.x - VigilState.dragStart.x);
    const h = Math.abs(VigilState.dragCurrent.y - VigilState.dragStart.y);
    ctx.save();
    ctx.strokeStyle = CATEGORY_COLORS.manual;
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 2]);
    ctx.strokeRect(x1, y1, w, h);
    ctx.restore();
  }
}

function getCanvasCoords(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: Math.round((event.clientX - rect.left) * scaleX),
    y: Math.round((event.clientY - rect.top) * scaleY),
  };
}

async function saveRegionCorrectionsToServer() {
  if (!VigilState.sessionId) return;
  const allRegs = [...VigilState.regions, ...VigilState.manualRegions];
  const activeIds = allRegs.filter((r) => r["active"]).map((r) => r["region_id"]);
  const excludedIds = allRegs.filter((r) => !r["active"]).map((r) => r["region_id"]);
  const manualPayload = VigilState.manualRegions.map((m) => ({
    region_id: m["region_id"],
    category: "manual",
    x1: m["bbox"]["x1"],
    y1: m["bbox"]["y1"],
    x2: m["bbox"]["x2"],
    y2: m["bbox"]["y2"],
    active: m["active"],
  }));

  try {
    const res = await fetch(`./api/sessions/${VigilState.sessionId}/regions`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        active_region_ids: activeIds,
        excluded_region_ids: excludedIds,
        manual_regions: manualPayload,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    showAlert(`Failed to sync region corrections: ${err.message}`);
  }
}

// ---------------------------------------------------------------------------
// 4. Execute VIGIL Pipeline & Populate Evaluation / Audit Views
// ---------------------------------------------------------------------------
function buildTransformationConfig() {
  const allRegs = [...VigilState.regions, ...VigilState.manualRegions];
  const activeIds = allRegs.filter((r) => r["active"]).map((r) => r["region_id"]);
  const excludedIds = allRegs.filter((r) => !r["active"]).map((r) => r["region_id"]);

  const activeSemanticClasses = Array.from(document.querySelectorAll(".sem-cls-chk"))
    .filter((chk) => chk.checked)
    .map((chk) => parseInt(chk.value, 10));

  const rgbParts = document
    .getElementById("inp-solid-rgb")
    .value.split(",")
    .map((x) => parseInt(x.trim(), 10))
    .filter((n) => !Number.isNaN(n));
  const solidRgb = rgbParts.length === 3 ? rgbParts : [24, 24, 24];

  const manualPayload = VigilState.manualRegions.map((m) => ({
    region_id: m["region_id"],
    category: "manual",
    x1: m["bbox"]["x1"],
    y1: m["bbox"]["y1"],
    x2: m["bbox"]["x2"],
    y2: m["bbox"]["y2"],
    active: m["active"],
  }));

  return {
    policy_id: document.getElementById("sel-policy").value,
    method: document.getElementById("sel-method").value,
    pixel_block_size: parseInt(document.getElementById("rng-pixel-block").value, 10),
    blur_kernel_size: parseInt(document.getElementById("rng-blur-kernel").value, 10),
    solid_color_rgb: solidRgb,
    mask_dilation_px: parseInt(document.getElementById("rng-mask-dilation").value, 10),
    noise_sigma: parseFloat(document.getElementById("rng-noise-sigma").value),
    freq_strength: parseFloat(document.getElementById("rng-freq-strength").value),
    apply_noise_to: document.getElementById("sel-noise-target").value,
    random_seed: parseInt(document.getElementById("inp-random-seed").value, 10) || 42,
    active_region_ids: activeIds,
    excluded_region_ids: excludedIds,
    active_semantic_classes: activeSemanticClasses,
    manual_regions: manualPayload,
    strip_metadata: true,
    apply_visible_watermark: document.getElementById("chk-watermark").checked,
  };
}

async function executeVigilPipeline() {
  showAlert(null);
  if (!VigilState.sessionId) {
    showAlert("Upload an image in Workspace first.");
    return;
  }

  const btnWs = document.getElementById("btn-execute-vigil");
  const btnLab = document.getElementById("btn-lab-execute");
  btnWs.disabled = true;
  btnLab.disabled = true;
  btnWs.textContent = "Executing VIGIL Pipeline...";

  try {
    const config = buildTransformationConfig();
    const res = await fetch("./api/vigil/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: VigilState.sessionId,
        config: config,
        run_evaluation: true,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data["detail"] || "VIGIL execution failed");
    }

    VigilState.urls.transformed = data["transformed_png_url"];
    VigilState.urls.mask = data["protection_mask_url"];
    VigilState.urls.heatmap = data["difference_heatmap_url"];

    document.getElementById("sel-ws-view-mode").value = "transformed";
    updateWorkspaceOutputViewport();

    const evalRep = data["evaluation_report"];
    const auditRep = data["audit_report"];

    if (evalRep) {
      document.getElementById("ws-ssim-summary").textContent = evalRep["full_image_ssim"];
      document.getElementById("ws-psnr-summary").textContent = `PSNR: ${evalRep["full_image_psnr_db"]} dB`;
      document.getElementById("ws-l1-summary").textContent = evalRep["protected_region_mean_l1_diff"];
    }
    if (auditRep) {
      document.getElementById("ws-coverage-summary").textContent =
        `Target mod ratio: ${(auditRep["modified_pixels_within_target_ratio"] * 100).toFixed(1)}%`;
      document.getElementById("ws-audit-badge").innerHTML = statusBadgeHtml(auditRep["overall_audit_status"]);
    }
    document.getElementById("ws-time-summary").textContent = `Latency: ${data["processing_time_ms"]} ms`;

    populateLabView(evalRep);
    populateAuditView(auditRep, data["transformation_history"] || []);
    markWorkflowStep(6);
    await refreshOverview();
  } catch (err) {
    showAlert(err.message);
  } finally {
    btnWs.disabled = false;
    btnLab.disabled = false;
    btnWs.textContent = "Execute VIGIL Transformation & Evaluation";
  }
}

function populateLabView(evalRep) {
  if (!evalRep) return;
  document.getElementById("lab-exp-id").textContent =
    `Experiment: ${evalRep["experiment_id"]} | Seed: ${evalRep["random_seed"]}`;

  const simTbody = document.getElementById("lab-similarity-tbody");
  simTbody.innerHTML = `
    <tr>
      <td><strong>Full Image</strong></td>
      <td class="mono">${evalRep["full_image_ssim"]}</td>
      <td class="mono">${evalRep["full_image_psnr_db"]}</td>
      <td class="mono">--</td>
      <td>Human visual similarity across the entire image canvas.</td>
    </tr>
    <tr>
      <td><strong>Unprotected Background</strong></td>
      <td class="mono">${evalRep["unprotected_background_ssim"]}</td>
      <td class="mono">${evalRep["unprotected_background_psnr_db"]}</td>
      <td class="mono">--</td>
      <td>Should be very close to 1.0 / high PSNR for solid/blur/pixelate methods.</td>
    </tr>
    <tr>
      <td><strong>Protected Region</strong></td>
      <td class="mono">${evalRep["protected_region_ssim"]}</td>
      <td class="mono">${evalRep["protected_region_psnr_db"]}</td>
      <td class="mono">${evalRep["protected_region_mean_l1_diff"]}</td>
      <td>Measures intensity of signal change inside target regions (does not by itself prove anonymity).</td>
    </tr>
  `;

  // Detector retention
  const detList = evalRep["detector_retention"] || [];
  document.getElementById("lab-retention-tbody").innerHTML = detList
    .map((d) => {
      let badge;
      if (d["count_before"] === 0) {
        badge = `<span class="badge">N/A</span>`;
      } else if (d["matched_regions_after"] === 0) {
        badge = `<span class="badge badge-pass">0 RE-DETECTED</span>`;
      } else {
        badge = `<span class="badge badge-warn">RETAINED ${d["matched_regions_after"]}/${d["count_before"]}</span>`;
      }
      return `
        <tr>
          <td>${escapeHtml(d["category"])}</td>
          <td class="mono">${escapeHtml(d["detector_name"])}</td>
          <td class="mono">${d["count_before"]}</td>
          <td class="mono">${d["count_after"]}</td>
          <td class="mono">${d["matched_regions_after"]}</td>
          <td class="mono">${d["retained_ratio"]}</td>
          <td>${badge}<div style="font-size:11px; color:var(--text-secondary); margin-top:3px;">${escapeHtml(d["status_note"])}</div></td>
        </tr>`;
    })
    .join("");

  // Controlled transformations (keys normalized to snake_case: jpeg_q75, resize_0_5x, gaussian_blur_3x3)
  const ctrlList = evalRep["controlled_transforms"] || [];
  document.getElementById("lab-transforms-tbody").innerHTML = ctrlList
    .map(
      (c) => `
      <tr>
        <td><strong>${escapeHtml(c["transform_name"])}</strong><br/><span class="mono" style="color:var(--text-muted)">${escapeHtml(c["transform_key"])}</span></td>
        <td class="mono">${c["ssim_vs_transformed"]}</td>
        <td class="mono">${c["psnr_vs_transformed_db"]}</td>
        <td class="mono">${c["perturbation_retention_ratio"]}</td>
        <td class="mono">${c["post_transform_face_detections"]}</td>
      </tr>`
    )
    .join("");
}

function populateAuditView(auditRep, historyList) {
  if (!auditRep) return;
  document.getElementById("aud-overall-badge").outerHTML =
    `<span id="aud-overall-badge" class="badge ${auditRep["overall_audit_status"] === "PASS" ? "badge-pass" : auditRep["overall_audit_status"] === "FAIL" ? "badge-fail" : "badge-warn"}">${auditRep["overall_audit_status"]}</span>`;

  const checks = auditRep["checks"] || {};
  document.getElementById("aud-checks-tbody").innerHTML = Object.entries(checks)
    .map(([checkKey, result]) => {
      const cls = result === "PASS" ? "badge-pass" : result === "FAIL" ? "badge-fail" : "badge-warn";
      return `<tr><td class="mono">${escapeHtml(checkKey)}</td><td><span class="badge ${cls}">${escapeHtml(result)}</span></td></tr>`;
    })
    .join("");

  const reasons = auditRep["status_reasons"] || [];
  document.getElementById("aud-reasons-list").innerHTML = reasons
    .map((r) => `<li>${escapeHtml(r)}</li>`)
    .join("");

  const sec = auditRep["security_verification"] || {};
  document.getElementById("aud-coverage-tbody").innerHTML = `
    <tr><th>System Mode</th><td class="mono">${escapeHtml(auditRep["system_mode"])}</td></tr>
    <tr><th>Total / Active / Excluded Regions</th><td class="mono">${auditRep["total_detected_regions"]} total | ${auditRep["active_protected_regions"]} active | ${auditRep["excluded_regions_count"]} excluded</td></tr>
    <tr><th>Target Mask Pixel Ratio</th><td class="mono">${(auditRep["target_mask_pixel_ratio"] * 100).toFixed(2)}% of image canvas</td></tr>
    <tr><th>Modified Pixels Inside Target</th><td class="mono">${(auditRep["modified_pixels_within_target_ratio"] * 100).toFixed(2)}%</td></tr>
    <tr><th>Unintended Background Modification</th><td class="mono">${(auditRep["unintended_background_modification_ratio"] * 100).toFixed(4)}%</td></tr>
    <tr><th>PNG Chunks Present</th><td class="mono">${(sec["chunks_present"] || []).join(", ")}</td></tr>
    <tr><th>Forbidden Metadata Chunks</th><td class="mono">${(sec["forbidden_metadata_chunks_found"] || []).length === 0 ? "NONE (Clean)" : sec["forbidden_metadata_chunks_found"].join(", ")}</td></tr>
    <tr><th>PNG CRC32 Checksums Valid</th><td class="mono">${sec["all_crc32_valid"] ? "YES" : "NO"}</td></tr>
    <tr><th>Output PNG SHA-256</th><td class="mono">${escapeHtml(sec["output_sha256"] || "--")}</td></tr>
  `;

  const lims = auditRep["evaluation_limitations"] || [];
  document.getElementById("aud-limitations-list").innerHTML = lims
    .map((l) => `<li>${escapeHtml(l)}</li>`)
    .join("");

  document.getElementById("aud-history-tbody").innerHTML = (historyList || [])
    .map(
      (h) => `
      <tr>
        <td class="mono">${h["step"]}</td>
        <td class="mono">${escapeHtml(h["method"])}</td>
        <td class="mono">${escapeHtml(h["policy_id"])}</td>
        <td class="mono">${h["random_seed"]}</td>
        <td class="mono">${h["active_regions"]}</td>
        <td class="mono">${(h["target_pixel_ratio"] * 100).toFixed(2)}%</td>
        <td class="mono">${h["full_image_ssim"] != null ? h["full_image_ssim"] : "--"}</td>
        <td>${statusBadgeHtml(h["overall_audit_status"])}</td>
        <td class="mono">${h["processing_time_ms"]}</td>
      </tr>`
    )
    .join("");

  document.getElementById("aud-json-viewer").textContent = JSON.stringify(auditRep, null, 2);
}

function updateExportLinks() {
  const sid = VigilState.sessionId;
  const pngLnk = document.getElementById("lnk-export-png");
  const jsonLnk = document.getElementById("lnk-export-json");
  const zipLnk = document.getElementById("lnk-export-zip");

  if (sid) {
    pngLnk.href = `./api/export/${sid}/image.png`;
    jsonLnk.href = `./api/export/${sid}/audit.json`;
    zipLnk.href = `./api/export/${sid}/bundle.zip`;
  } else {
    pngLnk.href = "#";
    jsonLnk.href = "#";
    zipLnk.href = "#";
  }
}

// ---------------------------------------------------------------------------
// Event Wiring
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-tab").forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.getAttribute("data-view")));
  });

  const bindSlider = (sliderId, labelId) => {
    const s = document.getElementById(sliderId);
    const l = document.getElementById(labelId);
    s.addEventListener("input", () => { l.textContent = s.value; });
  };
  bindSlider("rng-noise-sigma", "lbl-noise-sigma");
  bindSlider("rng-freq-strength", "lbl-freq-strength");
  bindSlider("rng-pixel-block", "lbl-pixel-block");
  bindSlider("rng-blur-kernel", "lbl-blur-kernel");
  bindSlider("rng-mask-dilation", "lbl-mask-dilation");

  document.getElementById("btn-refresh-overview").addEventListener("click", refreshOverview);
  document.getElementById("btn-upload-analyze").addEventListener("click", handleUploadAndAnalyze);
  document.getElementById("btn-execute-vigil").addEventListener("click", executeVigilPipeline);
  document.getElementById("btn-lab-execute").addEventListener("click", executeVigilPipeline);
  document.getElementById("sel-ws-view-mode").addEventListener("change", updateWorkspaceOutputViewport);

  document.getElementById("btn-lab-reeval").addEventListener("click", async () => {
    if (!VigilState.sessionId) return;
    const res = await fetch(`./api/vigil/evaluate/${VigilState.sessionId}`, { method: "POST" });
    const data = await res.json();
    if (res.ok && data["evaluation_report"]) {
      populateLabView(data["evaluation_report"]);
    } else {
      showAlert(data["detail"] || "Re-evaluation failed");
    }
  });

  const canvas = document.getElementById("detection-canvas");
  canvas.addEventListener("mousedown", (e) => {
    if (!VigilState.sessionId) return;
    VigilState.isDrawing = true;
    VigilState.dragStart = getCanvasCoords(canvas, e);
    VigilState.dragCurrent = { ...VigilState.dragStart };
  });
  canvas.addEventListener("mousemove", (e) => {
    if (!VigilState.isDrawing) return;
    VigilState.dragCurrent = getCanvasCoords(canvas, e);
    renderDetectionCanvas();
  });
  canvas.addEventListener("mouseup", () => {
    if (!VigilState.isDrawing) return;
    VigilState.isDrawing = false;
    const x1 = Math.max(0, Math.min(VigilState.dragStart.x, VigilState.dragCurrent.x));
    const y1 = Math.max(0, Math.min(VigilState.dragStart.y, VigilState.dragCurrent.y));
    const x2 = Math.min(canvas.width, Math.max(VigilState.dragStart.x, VigilState.dragCurrent.x));
    const y2 = Math.min(canvas.height, Math.max(VigilState.dragStart.y, VigilState.dragCurrent.y));

    if (x2 - x1 >= 8 && y2 - y1 >= 8) {
      const mId = `manual_${String(VigilState.manualRegions.length + 1).padStart(3, "0")}`;
      VigilState.manualRegions.push({
        region_id: mId,
        category: "manual",
        bbox: { x1, y1, x2, y2 },
        confidence: 1.0,
        detector_source: "User_Manual_Annotation",
        active: true,
        semantic_classes_present: [],
      });
      populateDetectionTable();
      updateRegionSummaryCounter();
    }
    renderDetectionCanvas();
  });

  document.getElementById("btn-clear-manual").addEventListener("click", () => {
    VigilState.manualRegions = [];
    populateDetectionTable();
    renderDetectionCanvas();
    updateRegionSummaryCounter();
  });

  document.getElementById("btn-save-regions").addEventListener("click", async () => {
    await saveRegionCorrectionsToServer();
    renderDetectionCanvas();
  });

  document.getElementById("btn-verify-png").addEventListener("click", async () => {
    const inp = document.getElementById("inp-verify-png");
    if (!inp.files || inp.files.length === 0) return;
    const fd = new FormData();
    fd.append("file", inp.files[0]);
    const res = await fetch("./api/security/verify-png", { method: "POST", body: fd });
    const data = await res.json();
    document.getElementById("pre-verify-png-result").textContent = JSON.stringify(data, null, 2);
  });

  document.getElementById("btn-purge-session").addEventListener("click", async () => {
    if (!VigilState.sessionId) return;
    await fetch(`./api/sessions/${VigilState.sessionId}`, { method: "DELETE" });
    VigilState.sessionId = null;
    document.getElementById("hdr-session-id").textContent = "PURGED";
    await refreshOverview();
  });

  refreshOverview();
});

/* RAKSHA Citizen — family mode (Part 1, Phase 2, task 2.2)
 *
 * The people who most need this app are the least able to judge a verdict.
 * Family mode changes what the *screen* does, never what the *scorer* says —
 * it re-presents, it does not re-score. That separation matters: a lenient or
 * strict UI must never alter a verdict, or the same input would get two answers
 * depending on who is holding the phone.
 *
 * Three behaviours, in order of importance:
 *
 *   STRICTER  a MODERATE band becomes actionable on screen instead of staying
 *             advisory. For a 71-year-old, "some warning signs are present" is
 *             not a sentence that leads to action.
 *   LOUDER    larger type, no auto-dismiss.
 *   SIMPLER   the severity slider is hidden on the report screen, because a
 *             frightened person should not be asked to rate the crime.
 *
 * Stored only in localStorage. Never sent anywhere. There is no account, no
 * sync, no server-side profile — that is a Part 1 §8 constraint, not a TODO.
 */

"use strict";

var FAMILY_STORAGE_KEY = "raksha.family.enabled";

/** Bands that become actionable when family mode is on. */
var FAMILY_ESCALATED_BANDS = Object.freeze(["MODERATE"]);

function familyDefaults() {
  return {
    enabled: false,
    escalateModerate: true,
    hideSeveritySlider: true,
    largerType: true,
  };
}

/**
 * Read the stored preference.
 *
 * Fails closed in the direction that helps: if localStorage is unavailable or
 * holds garbage, family mode is OFF rather than silently on. A mode that
 * appears without the user asking would be its own kind of false claim.
 */
function readFamily(store) {
  var out = familyDefaults();
  if (!store) return out;
  try {
    var raw = store.getItem(FAMILY_STORAGE_KEY);
    out.enabled = raw === "1" || raw === "true";
  } catch (err) {
    out.enabled = false;
  }
  return out;
}

function writeFamily(store, enabled) {
  if (!store) return false;
  try {
    store.setItem(FAMILY_STORAGE_KEY, enabled ? "1" : "0");
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Decide how a verdict should be shown. Pure: same input, same output, no
 * storage access, so it can be tested without a browser.
 *
 * This function never changes `verdict`. It only decides emphasis and whether
 * the screen demands action.
 */
function presentVerdict(verdict, family) {
  var fam = family || familyDefaults();
  var band = String(verdict || "MODERATE").toUpperCase();
  var escalate = fam.enabled && fam.escalateModerate &&
    FAMILY_ESCALATED_BANDS.indexOf(band) >= 0;

  return {
    band: band,
    // The verdict the model produced. Unchanged, always.
    verdictUnchanged: true,
    actionable: escalate || band === "HIGH" || band === "CRITICAL",
    escalated: escalate,
    cssClasses: [
      "verdict",
      band,
      fam.enabled && fam.largerType ? "family-type" : "",
      escalate ? "family-escalated" : "",
    ].filter(Boolean),
    // In family mode a non-actionable band still must not read as reassurance.
    footnote: escalate ? "family-escalated" : "",
  };
}

/** Should the report screen's severity slider be hidden? */
function hideSeveritySlider(family) {
  var fam = family || familyDefaults();
  return Boolean(fam.enabled && fam.hideSeveritySlider);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    FAMILY_STORAGE_KEY: FAMILY_STORAGE_KEY,
    FAMILY_ESCALATED_BANDS: FAMILY_ESCALATED_BANDS,
    familyDefaults: familyDefaults,
    readFamily: readFamily,
    writeFamily: writeFamily,
    presentVerdict: presentVerdict,
    hideSeveritySlider: hideSeveritySlider,
  };
}
if (typeof window !== "undefined") {
  window.RakshaFamily = {
    FAMILY_STORAGE_KEY: FAMILY_STORAGE_KEY,
    familyDefaults: familyDefaults,
    readFamily: readFamily,
    writeFamily: writeFamily,
    presentVerdict: presentVerdict,
    hideSeveritySlider: hideSeveritySlider,
  };
}

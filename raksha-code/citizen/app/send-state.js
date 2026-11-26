/* RAKSHA Citizen — "why did the send fail?" (Part Four, task 4.2)
 *
 * Kept in its own file for one reason: so it can be tested.
 *
 * This logic used to be implicit. `api()` threw on a non-OK response and every
 * caller read *any* throw as "offline", so a 422 from the server and a phone with
 * no signal produced the same citizen-facing sentence — "saved on this phone and
 * will be sent when you are back online". A 4xx will never succeed on retry, so
 * that sentence is a promise nothing can keep.
 *
 * The distinction matters more than the wording: a report kept for a retry it
 * can never pass is a report the user believes is filed and is not.
 *
 * Four outcomes:
 *   sent      — the server accepted it
 *   retry     — worth trying again (offline, DNS, 5xx, timeout)
 *   rejected  — the server said no and will keep saying no (4xx)
 *   unknown   — nothing was attempted
 */

"use strict";

var SENT = "sent";
var RETRY = "retry";
var REJECTED = "rejected";
var UNKNOWN = "unknown";

/* Statuses that mean "slow down, try later" rather than "this is wrong".
 * 429 is the one 4xx that IS worth retrying, so it cannot be swept into the
 * rejected bucket by a naive `>= 400` rule. */
var RETRYABLE_4XX = Object.freeze([408, 429]);

/**
 * Classify a failed send.
 *
 * @param {*} err  null/undefined for success, or an Error, optionally carrying
 *                 a numeric `status` (set by `api()` from the response).
 * @returns {string} sent | retry | rejected | unknown
 */
function classifySend(err) {
  if (err === null || err === undefined) return SENT;

  var status = err && typeof err.status === "number" ? err.status : null;

  if (status === null) {
    /* No status attached: the request never got an answer (offline, DNS,
     * CORS, timeout). That is the one case where "try again later" is right. */
    return RETRY;
  }

  if (status >= 200 && status < 300) return SENT;

  if (status >= 400 && status < 500) {
    return RETRYABLE_4XX.indexOf(status) >= 0 ? RETRY : REJECTED;
  }

  if (status >= 500) return RETRY;

  return UNKNOWN;
}

/** The sentence a citizen should read for each outcome. */
var SEND_COPY = Object.freeze({
  sent: "Report sent.",
  retry: "No signal. Your report is kept on this device and will be sent " +
         "automatically when you are back online.",
  rejected: "The service refused this report. Nothing is queued. Call 1930 instead.",
  unknown: "Report not sent. Call 1930 instead.",
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    classifySend: classifySend,
    SEND_COPY: SEND_COPY,
    SENT: SENT,
    RETRY: RETRY,
    REJECTED: REJECTED,
    UNKNOWN: UNKNOWN,
  };
}
if (typeof window !== "undefined") {
  window.RakshaSend = {
    classifySend: classifySend,
    SEND_COPY: SEND_COPY,
  };
}

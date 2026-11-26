/* RAKSHA Citizen — offline report queue (Part 1, Phase 3, task 3.6)
 *
 * Fraud happens on the worst network. A report that is lost because the phone
 * had no signal is a report that never existed, and telling someone "sent" when
 * it is sitting in a queue is a lie of the exact kind this app refuses to tell.
 *
 * Design constraints, all of them from Part 1 §8:
 *
 *   * The queue stores only what the report rail already sends: category, a
 *     severity band, a language tag and (optionally) an opaque case token.
 *     No audio, no message text, no phone number. Ever.
 *   * It is bounded. An unbounded queue on a low-storage phone is a way to
 *     brick the device; 50 pending reports is far more than any real use.
 *   * It is app-scoped and purgeable. One call empties it.
 *   * A queued report is NEVER reported as sent. The caller must read
 *     `state` and show the "saved on this phone" copy.
 */

"use strict";

var QUEUE_KEY = "raksha.report.queue.v1";
var QUEUE_MAX = 50;

/* The only fields that may ever be persisted. Anything else is dropped, so a
 * caller cannot smuggle content into storage by adding a key. */
var ALLOWED_FIELDS = Object.freeze(["category", "severity", "lang", "case_id"]);

function sanitise(entry) {
  var out = {};
  if (!entry || typeof entry !== "object") return out;
  for (var i = 0; i < ALLOWED_FIELDS.length; i++) {
    var k = ALLOWED_FIELDS[i];
    if (entry[k] === undefined || entry[k] === null) continue;
    if (k === "severity") {
      var n = Number(entry[k]);
      out[k] = isFinite(n) ? Math.max(0, Math.min(1, n)) : 0.5;
    } else {
      out[k] = String(entry[k]).slice(0, 64);
    }
  }
  return out;
}

function readQueue(store) {
  if (!store) return [];
  try {
    var raw = store.getItem(QUEUE_KEY);
    if (!raw) return [];
    var parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map(sanitise).filter(function (e) {
      return e && typeof e.category === "string" && e.category;
    });
  } catch (err) {
    return [];
  }
}

function writeQueue(store, items) {
  if (!store) return false;
  try {
    store.setItem(QUEUE_KEY, JSON.stringify(items));
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Add a report to the queue. Oldest entries are dropped once the cap is
 * reached — a phone that runs out of storage fails at everything else too.
 */
function enqueue(store, entry) {
  var clean = sanitise(entry);
  if (!clean.category) return {ok: false, reason: "category required", size: 0};
  var items = readQueue(store);
  items.push(clean);
  if (items.length > QUEUE_MAX) items = items.slice(items.length - QUEUE_MAX);
  var ok = writeQueue(store, items);
  return {ok: ok, reason: ok ? "" : "storage unavailable", size: items.length};
}

function size(store) {
  return readQueue(store).length;
}

function clear(store) {
  if (!store) return false;
  try {
    store.removeItem(QUEUE_KEY);
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Attempt to flush the queue through a sender.
 *
 * `send` receives one sanitised entry and must return a promise (or a value)
 * that resolves truthy on success. Entries are removed ONLY when the send
 * succeeds — a failed flush must not lose the backlog. The flush stops at the
 * first failure so ordering is preserved and a dead network is not hammered.
 */
function flush(store, send) {
  var items = readQueue(store);
  if (!items.length) return Promise.resolve({sent: 0, remaining: 0});

  var sent = 0;
  var i = 0;

  function step() {
    if (i >= items.length) {
      writeQueue(store, items.slice(sent));
      return {sent: sent, remaining: items.length - sent};
    }
    return Promise.resolve()
      .then(function () { return send(items[i]); })
      .then(function (ok) {
        if (!ok) {
          writeQueue(store, items.slice(sent));
          return {sent: sent, remaining: items.length - sent};
        }
        sent += 1;
        i += 1;
        return step();
      })
      .catch(function () {
        writeQueue(store, items.slice(sent));
        return {sent: sent, remaining: items.length - sent};
      });
  }

  return Promise.resolve(step());
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    QUEUE_KEY: QUEUE_KEY,
    QUEUE_MAX: QUEUE_MAX,
    ALLOWED_FIELDS: ALLOWED_FIELDS,
    sanitise: sanitise,
    readQueue: readQueue,
    enqueue: enqueue,
    size: size,
    clear: clear,
    flush: flush,
  };
}
if (typeof window !== "undefined") {
  window.RakshaQueue = {
    QUEUE_MAX: QUEUE_MAX,
    readQueue: readQueue,
    enqueue: enqueue,
    size: size,
    clear: clear,
    flush: flush,
  };
}

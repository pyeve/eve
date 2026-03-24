# Security Report Review — Eve Framework

Thank you for taking the time to analyze the Eve codebase and submit these six security reports. We take security seriously and have carefully reviewed each finding against the current codebase.

After thorough analysis, we found that **one report (#4) identified a genuine code defect**, which we have already fixed. The remaining five reports describe attack vectors that are either already mitigated by Eve's default configuration or based on an incorrect understanding of the code flow.

Below is our detailed response to each report, followed by a summary.

---

## Report #1 — MongoDB Query Injection via Unsanitized 'where' Parameter (CVSS 8.7)

**Assessment: Mostly mitigated; documentation improved.**

Two of the three PoC examples are already mitigated by Eve's default configuration:

- `{"$where": "sleep(5000)"}` — **blocked**. `$where` is in `MONGO_QUERY_BLACKLIST` by default since Eve 0.7.x (and the recursive traversal bypass was fixed in 0.7.10).
- `{"email": {"$regex": ".*"}}` — **blocked**. `$regex` is also in the default blacklist.

The third PoC (`{"password": {"$gt": ""}}`) does work with default settings, as `$gt` is a legitimate MongoDB comparison operator required for normal API operation (e.g., date range queries).

**Regarding `auth_field` bypass:** the report states that injected conditions can bypass `auth_field`-protected resources. This is inaccurate — the `auth_field` filter is applied server-side as an additional AND condition on the query. A client-supplied `where` clause cannot override or remove it; documents belonging to other users are not returned.

**Regarding the actual risk:** with the default configuration (`ALLOWED_FILTERS = ['*']`), comparison operators like `$gt`/`$lt`/`$ne` can be used for blind enumeration of field values on any filterable field. This is a known trade-off of Eve's design as a flexible REST framework — it intentionally exposes MongoDB's query language to API consumers. Eve provides the configuration tools to mitigate this (`ALLOWED_FILTERS`, `VALIDATE_FILTERS`, `MONGO_QUERY_BLACKLIST`), and we have now strengthened the documentation with explicit security warnings about this.

We do not consider this a code vulnerability warranting a CVE, as the framework behaves as designed and provides adequate configuration options for hardening.

---

## Report #2 — MongoDB Operator Injection via $where JavaScript Execution (CVSS 9.3)

**Assessment: Not a vulnerability.**

While `$where` is listed in the `Mongo.operators` set (the set of *recognized* MongoDB operators), it is also included in `MONGO_QUERY_BLACKLIST`, which defaults to `['$where', '$regex']`. The `_sanitize()` method in `eve/io/mongo/mongo.py` checks incoming queries against this blacklist and aborts with a 400 error if any blacklisted operator is found. This check is applied recursively to nested query structures.

All PoCs in this report — both the DoS via busy-loop and the blind extraction via boolean/timing channels — are rejected with a 400 response under default settings. The `$where` operator would only be executable if an administrator explicitly removes it from `MONGO_QUERY_BLACKLIST`, which is a deliberate opt-in.

The CVSS 9.3 rating is not applicable as the attack surface does not exist under default configuration.

---

## Report #3 — MongoDB ReDoS via Uncontrolled $regex Operator (CVSS 8.7)

**Assessment: Not a vulnerability.**

This report follows the same pattern as #2. While `$regex` is listed in the `Mongo.operators` set, it is **also included in `MONGO_QUERY_BLACKLIST`**, which defaults to `['$where', '$regex']`.

All PoCs — including the catastrophic backtracking patterns — are rejected with a 400 response under default settings. The `_sanitize()` method blocks `$regex` before the query ever reaches MongoDB. The operator would only be usable if an administrator explicitly removes it from the blacklist.

The CVSS 8.7 rating is not applicable as the attack surface does not exist under default configuration.

---

## Report #4 — JSONP Callback Injection via Unvalidated User Input (CVSS 7.1)

**Assessment: Valid finding. Fixed.**

When JSONP support was explicitly enabled via `JSONP_ARGUMENT`, the callback parameter was interpolated into the response without validation, allowing arbitrary JavaScript injection.

We have addressed this with two changes:

1. **Fix:** The JSONP callback is now validated against a strict pattern (`^[a-zA-Z_$][\w$.]*$`) ensuring only valid JavaScript identifiers are accepted. Invalid callback names are rejected with a 400 response.

2. **Deprecation:** `JSONP_ARGUMENT` is now deprecated and will be removed in a future release. JSONP is a legacy technology superseded by CORS, which Eve already supports. A `DeprecationWarning` is emitted at startup when the setting is configured.

We note that the CVSS 7.1 rating overstates the practical impact: JSONP is disabled by default (`JSONP_ARGUMENT = None`) and requires explicit opt-in.

---

## Report #5 — IDOR via Auth Field Bypass on PUT with Upsert (CVSS 5.9)

**Assessment: Not a vulnerability.**

The report claims that during the PUT upsert path, an attacker can supply an arbitrary `auth_field` value in the request body to create documents attributed to another user. This is incorrect.

When `UPSERT_ON_PUT` triggers `post_internal()`, the function calls `resolve_user_restricted_access()` (in `eve/methods/common.py`), which **unconditionally overwrites** the `auth_field` with the authenticated user's identity:

```python
document[auth_field] = request_auth_value
```

This is not a conditional assignment — any attacker-supplied value is replaced with the real authenticated user's identity before the document is persisted. The PoC would result in a document owned by `user_b` (the actual authenticated user), not `user_a` as claimed.

---

## Report #6 — GridFS Arbitrary File Retrieval via ObjectId Manipulation (CVSS 7.1)

**Assessment: Not a vulnerability as described.**

The specific attack path described — accessing files across resources via resource endpoints — is inaccurate. When media fields are embedded in documents (the default behavior, `RETURN_MEDIA_AS_URL = False`), file content is served as part of the document response and goes through the normal document retrieval pipeline, including `auth_field` enforcement and all access control checks.

We acknowledge a tangential concern: when `RETURN_MEDIA_AS_URL` is set to `True` (not the default), the global `/media/<ObjectId>` endpoint serves files from GridFS based solely on the ObjectId, with only generic authentication and no ownership check. This is a known design choice — the ObjectId acts as an opaque capability token, and access control is enforced at the document level. ObjectIds must be known to be exploited and are only revealed through authorized document access.

The PoC conflates resource endpoints with the media endpoint and does not demonstrate the claimed attack.

---

## Summary

| # | Report | CVSS | Assessment | Action Taken |
|---|--------|------|------------|--------------|
| 1 | MongoDB Query Injection via `where` | 8.7 | Mostly mitigated by default | Improved documentation |
| 2 | `$where` JavaScript Execution | 9.3 | Blocked by default blacklist | None required |
| 3 | `$regex` ReDoS | 8.7 | Blocked by default blacklist | None required |
| 4 | JSONP Callback Injection | 7.1 | **Valid** (opt-in feature) | Fixed + deprecated JSONP |
| 5 | IDOR via Auth Field on PUT Upsert | 5.9 | Incorrect — auth_field is overwritten | None required |
| 6 | GridFS IDOR via ObjectId | 7.1 | Inaccurate attack path | None required |

Reports #2 and #3 appear to have been produced by analyzing the `Mongo.operators` set in isolation, without tracing the full query pipeline through the `_sanitize()` method and `MONGO_QUERY_BLACKLIST`. We encourage future analysis to follow the complete code path from request to database execution.

We appreciate the effort in examining Eve's security posture and welcome further reports that identify actual code defects.

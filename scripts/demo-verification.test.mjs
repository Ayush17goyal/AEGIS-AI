import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve, dirname } from "node:path";
import vm from "node:vm";
import ts from "typescript";

// Transpile with the project's installed TypeScript; no new test dependency.
const require = createRequire(import.meta.url);
const cache = new Map();
function load(path) {
  const absolute = resolve(path);
  if (cache.has(absolute)) return cache.get(absolute);
  const module = { exports: {} };
  cache.set(absolute, module.exports);
  const source = readFileSync(absolute, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const scopedRequire = (name) => {
    if (name === "../main")
      return {
        api: () => Promise.reject(new Error("No network in unit tests")),
      };
    if (name.startsWith("."))
      return load(
        resolve(
          dirname(absolute),
          name +
            (name.endsWith("presets") || name.endsWith("demoVerification")
              ? ".ts"
              : ".tsx"),
        ),
      );
    return require(name);
  };
  vm.runInThisContext(`(function(require,module,exports){${output}\n})`, {
    filename: absolute,
  })(scopedRequire, module, module.exports);
  cache.set(absolute, module.exports);
  return module.exports;
}
const {
  FEATURE_PRESETS: presets,
  PRESET_CATEGORIES: categories,
  DEMO_TOUR_STEPS: tour,
} = load("src/presets.ts");
const {
  verifyDemo,
  presetUnavailable,
  writePresetHandoff,
  readPresetHandoff,
  safeDemoEvidence,
  readinessError,
  presetExecutionBlocked,
} = load("src/demoVerification.ts");
test("retained scenarios may request backend receipts while model dependencies are missing", () => {
  assert.equal(presetExecutionBlocked(presets.find((p) => p.id === "preset-contact-pii"), "bob"), null);
});
test("execution still blocks unsupported cards and incorrect personas", () => {
  assert.match(presetExecutionBlocked(presets.find((p) => p.id === "preset-secret-bearer"), "bob"), /OUT OF SCOPE/);
  assert.match(presetExecutionBlocked(presets.find((p) => p.id === "preset-rag-authorized"), "bob"), /Sign in/);
});
test("chat preset survives refresh through ID-only route state", () => {
  const storage = { getItem: () => null, removeItem: () => {} };
  assert.equal(readPresetHandoff(storage, "preset-contact-pii").id, "preset-contact-pii");
  assert.equal(readPresetHandoff(storage, "preset-contact-pii").id, "preset-contact-pii");
  assert.equal(readPresetHandoff(storage, "unknown-preset"), null);
});
test("readiness 404 identifies an outdated backend", () => {
  assert.match(readinessError({ status: 404 }), /outdated.*Restart FastAPI/);
});
test("readiness 401 explains session renewal", () => {
  assert.match(readinessError({ status: 401 }), /session expired.*sign in again/);
});
test("readiness proxy failure explains server startup", () => {
  assert.match(readinessError({ status: 502 }), /Start FastAPI on port 8000/);
});
test("readiness permission error is actionable", () => {
  assert.match(readinessError({ status: 403 }), /authorized account/);
});
test("readiness network failure never claims a missing model result", () => {
  assert.match(readinessError(new Error("network")), /Check the connection/);
  assert.doesNotMatch(readinessError(null), /NOT IMPLEMENTED/);
});
const preset = (id) => presets.find((item) => item.id === id);
const pii = preset("preset-contact-pii");
const denied = preset("preset-rag-denied");
const live = {
  pipeline_ready: true,
  demo_login_enabled: true,
  execution_mode: "live",
  components: [],
};
const unavailable = { ...live, pipeline_ready: false, execution_mode: "mock" };
const result = (overrides = {}) => ({
  id: "receipt-1",
  execution_status: "COMPLETED",
  action: "MASK",
  model_called: true,
  provider: "hosted",
  identity: "alice",
  reason_code: "INPUT_MASKED",
  response: "Safe answer",
  sanitized_prompt: "Contact [EMAIL_1], [PHONE_1]",
  context_count: 0,
  stages: pii.requiredStages,
  ...overrides,
});
const denyResult = (overrides = {}) =>
  result({
    action: "BLOCK",
    model_called: false,
    identity: "bob",
    provider: "not_called",
    reason_code: "AUTHORIZATION_DENIED",
    sanitized_prompt: null,
    stages: ["auth", "authorization"],
    ...overrides,
  });
const verdict = (value, selected = pii, status = live, actor = "alice") =>
  verifyDemo(selected, value, status, actor).status;

test("all 20 historical IDs remain unique; scope is 15 retained / 3 excluded / 2 pending", () => {
  assert.equal(presets.length, 20);
  assert.equal(new Set(presets.map((item) => item.id)).size, 20);
  assert.equal(
    presets.filter((item) => item.availability === "retained").length,
    15,
  );
  assert.equal(
    presets.filter((item) => item.availability === "out-of-scope").length,
    3,
  );
  assert.equal(
    presets.filter((item) => item.availability === "not-implemented").length,
    2,
  );
});
test("OUTPUT is filterable and tour includes pending output verification", () => {
  assert.ok(categories.some((item) => item.id === "OUTPUT"));
  assert.ok(tour.some((item) => item.presetId === "preset-output-redact"));
  assert.ok(tour.every((item) => preset(item.presetId)));
});
test("input scenario passes only complete live contract evidence", () =>
  assert.equal(verdict(result()), "PASS"));
test("legacy two-field action/model match is an ERROR", () =>
  assert.equal(verdict({ action: "MASK", model_called: true }), "ERROR"));
test("mock execution cannot pass", () =>
  assert.equal(verdict(result({ provider: "mock" })), "FAIL"));
test("unready pipeline cannot pass a full pipeline scenario", () =>
  assert.equal(verdict(result(), pii, unavailable), "NOT IMPLEMENTED"));
test("gateway NOT IMPLEMENTED is never a pass", () =>
  assert.equal(
    verdict(
      result({
        execution_status: "NOT IMPLEMENTED",
        model_called: false,
        missing_components: ["Laya"],
      }),
    ),
    "NOT IMPLEMENTED",
  ));
test("unavailable pipeline invoking model fails closed assertion", () =>
  assert.equal(
    verdict(result({ execution_status: "NOT IMPLEMENTED" })),
    "FAIL",
  ));
test("gateway errors stay ERROR", () =>
  assert.equal(verdict(result({ execution_status: "ERROR" })), "ERROR"));
for (const field of [
  "id",
  "reason_code",
  "provider",
  "action",
  "model_called",
  "response",
  "context_count",
  "sanitized_prompt",
]) {
  test(`missing required receipt field ${field} is ERROR`, () => {
    const value = result();
    delete value[field];
    assert.equal(verdict(value), "ERROR");
  });
}
test("incorrect gateway identity fails", () =>
  assert.equal(verdict(result({ identity: "bob" })), "FAIL"));
test("action mismatch fails", () =>
  assert.equal(verdict(result({ action: "ALLOW" })), "FAIL"));
test("model invocation mismatch fails", () =>
  assert.equal(verdict(result({ model_called: false })), "FAIL"));
test("raw contact in sanitized preview fails", () =>
  assert.equal(
    verdict(result({ sanitized_prompt: "phone +91 98765 43210" })),
    "FAIL",
  ));
test("raw contact in output fails and is withheld from evidence", () => {
  const response = "Call 9876543210";
  assert.equal(verdict(result({ response })), "FAIL");
  assert.ok(!safeDemoEvidence(response, pii).includes("9876543210"));
});
test("masking without sanitized preview fails", () =>
  assert.equal(verdict(result({ sanitized_prompt: null })), "FAIL"));
test("missing output stage cannot pass input scenario", () =>
  assert.equal(
    verdict(
      result({
        stages: pii.requiredStages.filter((item) => item !== "output_presidio"),
      }),
    ),
    "NOT IMPLEMENTED",
  ));
test("malformed stages or missing components is ERROR", () => {
  assert.equal(verdict(result({ stages: {} })), "ERROR");
  assert.equal(
    verdict(
      result({ execution_status: "NOT IMPLEMENTED", missing_components: {} }),
    ),
    "ERROR",
  );
});
test("indirect fixture uses approved input inspectors without a legacy CTX assertion", () => {
  const value = preset("preset-inj-indirect");
  assert.equal(value.availability, "retained");
  assert.ok(value.requiredStages.includes("nemo_input"));
  assert.ok(value.requiredStages.includes("laya_input"));
  assert.ok(!value.summary.includes("CTX-001"));
});
test("authorized RAG without context fails", () => {
  const selected = preset("preset-rag-authorized");
  assert.equal(
    verdict(
      result({
        action: "ALLOW",
        sanitized_prompt: "Safe",
        stages: selected.requiredStages,
      }),
      selected,
    ),
    "FAIL",
  );
});
test("ACL-only denial passes independently of missing Laya with accurate scope", () => {
  const verification = verifyDemo(denied, denyResult(), unavailable, "bob");
  assert.equal(verification.status, "PASS");
  assert.match(verification.details.join(" "), /Authorization-only/);
  assert.match(verification.details.join(" "), /does not verify NeMo/);
});
for (const override of [
  { action: "ACCESS DENY" },
  { model_called: true },
  { context_count: 1 },
  { reason_code: "OTHER" },
  { identity: "alice" },
  { provider: "mock" },
  { stages: ["auth", "authorization", "llm"] },
]) {
  test(`ACL rejects invalid denial ${JSON.stringify(override)}`, () =>
    assert.equal(
      verdict(denyResult(override), denied, unavailable, "bob"),
      "FAIL",
    ));
}
test("ACL requires auth and authorization stages", () =>
  assert.equal(
    verdict(
      denyResult({ stages: ["authorization"] }),
      denied,
      unavailable,
      "bob",
    ),
    "NOT IMPLEMENTED",
  ));
test("ACL refuses wrong selected persona before execution", () =>
  assert.match(presetUnavailable(denied, unavailable, "alice"), /Sign in as/));
test("ACL runs while full pipeline is unavailable", () =>
  assert.equal(presetUnavailable(denied, unavailable, "bob"), null));
test("output input-mask fixture never proves generated-output protection", () =>
  assert.equal(
    verdict(result(), preset("preset-output-redact")),
    "NOT IMPLEMENTED",
  ));
test("ID-only handoff resolves catalog, is consumed, and never stores prompt", () => {
  const values = new Map();
  const storage = {
    setItem: (key, value) => values.set(key, value),
    getItem: (key) => values.get(key),
    removeItem: (key) => values.delete(key),
  };
  writePresetHandoff(pii.id, storage);
  assert.deepEqual(JSON.parse(values.get("aegis-selected-preset")), {
    preset_id: pii.id,
  });
  assert.equal(readPresetHandoff(storage).id, pii.id);
  assert.equal(values.size, 0);
  for (const value of [
    "bad JSON",
    "null",
    JSON.stringify({ preset_id: "unknown" }),
    JSON.stringify({ prompt: "untrusted" }),
    JSON.stringify({ preset_id: "preset-secret-bearer" }),
  ]) {
    values.set("aegis-selected-preset", value);
    assert.equal(readPresetHandoff(storage), null);
    assert.equal(values.size, 0);
  }
});
test("server-rendered studio preserves card anatomy, pending handoffs and nonadmin guidance", () => {
  const React = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");
  const { MemoryRouter } = require("react-router-dom");
  const { FeatureDemos } = load("src/components/FeatureDemos.tsx");
  const html = renderToStaticMarkup(
    React.createElement(
      MemoryRouter,
      null,
      React.createElement(FeatureDemos, {
        user: { id: "bob", name: "Bob", role: "employee" },
        onSwitchPersona: () => {
          throw new Error("Must not auto-switch");
        },
      }),
    ),
  );
  for (const name of [
    "preset-title",
    "preset-summary",
    "preset-talking-box",
    "preset-talking-header",
    "preset-talking-list",
    "preset-payload-box",
  ])
    assert.ok(html.includes(name));
  assert.equal((html.match(/class="preset-card-full"/g) || []).length, 20);
  assert.ok(html.includes("sign out and sign in"));
  assert.ok(!html.includes("Switch to admin"));
  assert.equal(
    (html.match(/class="preset-chat-btn" disabled=""/g) || []).length,
    3,
  );
  assert.ok(!html.includes("INVARIANT VERIFIED"));
});

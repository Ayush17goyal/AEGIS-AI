import { FEATURE_PRESETS, type DemoPreset } from "./presets";

export function readinessError(error: unknown): string {
  const status = error && typeof error === "object" && "status" in error ? error.status : null;
  if (status === 401) return "ERROR: your session expired or the backend restarted. Sign out and sign in again.";
  if (status === 404) return "ERROR: the running backend is outdated and has no readiness endpoint. Restart FastAPI from this project, then sign in again.";
  if (status === 403) return "ERROR: this account cannot read pipeline readiness. Sign in with an authorized account.";
  if (status === 502 || status === 503 || status === 504) return "ERROR: the backend is unavailable. Start FastAPI on port 8000, then refresh readiness.";
  return "ERROR: unable to check backend readiness. Check the connection, retry, or sign in again.";
}

export type DemoStatus = {
  demo_login_enabled: boolean;
  pipeline_ready: boolean;
  components: { name: string; status: string; detail: string }[];
  execution_mode: "mock" | "live";
};
export type DemoResult = {
  id: string;
  action: string;
  model_called: boolean;
  provider: string;
  response: string;
  sanitized_prompt: string | null;
  context_count: number;
  reason?: string;
  execution_status: "NOT IMPLEMENTED" | "ERROR" | "COMPLETED";
  missing_components?: string[];
  reason_code?: string;
  stages?: string[];
  identity?: string;
  latency?: number;
  findings?: { category: string; kind: string; confidence: number }[];
};
export type Verification = {
  status: "PASS" | "FAIL" | "ERROR" | "NOT IMPLEMENTED";
  details: string[];
};

export function presetUnavailable(
  preset: DemoPreset,
  status: DemoStatus | null,
  userId: string,
): string | null {
  if (preset.availability !== "retained") return preset.availabilityReason;
  if (!status)
    return "NOT IMPLEMENTED: pipeline status has not been established.";
  if (preset.recommendedRole !== "any" && preset.recommendedRole !== userId)
    return `Sign in as ${preset.recommendedRoleName} before running this scenario.`;
  if (preset.id === "preset-rag-denied") return null;
  if (!status.pipeline_ready || status.execution_mode !== "live")
    return "NOT IMPLEMENTED: approved live pipeline is unavailable. Mock execution cannot verify a live scenario.";
  return null;
}

// Readiness describes capability, not whether the user may request a truthful
// backend receipt. Missing components are reported by the gateway, never bypassed.
export function presetExecutionBlocked(preset: DemoPreset, userId: string): string | null {
  if (preset.availability !== "retained") return preset.availabilityReason;
  if (preset.recommendedRole !== "any" && preset.recommendedRole !== userId)
    return `Sign in as ${preset.recommendedRoleName} before running this scenario.`;
  return null;
}

export function verifyDemo(
  preset: DemoPreset,
  result: DemoResult,
  status: DemoStatus | null,
  actorId: string,
): Verification {
  const answer = (
    state: Verification["status"],
    ...details: string[]
  ): Verification => ({ status: state, details });
  if (!result || typeof result !== "object")
    return answer("ERROR", "Malformed demo response.");
  if (
    (result.missing_components !== undefined &&
      (!Array.isArray(result.missing_components) ||
        !result.missing_components.every(
          (item) => typeof item === "string",
        ))) ||
    (result.stages !== undefined &&
      (!Array.isArray(result.stages) ||
        !result.stages.every((item) => typeof item === "string")))
  )
    return answer("ERROR", "Malformed component or stage evidence.");
  if (result.execution_status === "ERROR")
    return answer(
      "ERROR",
      typeof result.reason_code === "string"
        ? result.reason_code
        : "Gateway execution failed.",
    );
  if (result.execution_status === "NOT IMPLEMENTED") {
    if (
      result.model_called === true ||
      (typeof result.context_count === "number" && result.context_count > 0)
    )
      return answer(
        "FAIL",
        "Unavailable pipeline processed model/context data instead of failing closed.",
      );
    return answer(
      "NOT IMPLEMENTED",
      typeof result.reason_code === "string"
        ? result.reason_code
        : "Required pipeline components are unavailable.",
      ...(result.missing_components || []),
    );
  }
  if (
    result.execution_status !== "COMPLETED" ||
    typeof result.id !== "string" ||
    !result.id.trim() ||
    typeof result.action !== "string" ||
    typeof result.model_called !== "boolean" ||
    typeof result.provider !== "string" ||
    typeof result.response !== "string" ||
    !Number.isInteger(result.context_count) ||
    result.context_count < 0 ||
    !(
      result.sanitized_prompt === null ||
      typeof result.sanitized_prompt === "string"
    ) ||
    typeof result.reason_code !== "string" ||
    !result.reason_code.trim()
  ) {
    return answer(
      "ERROR",
      "Missing or malformed execution ID, reason code or result provenance.",
    );
  }
  if (preset.recommendedRole !== "any" && actorId !== preset.recommendedRole)
    return answer("FAIL", "Run identity does not match the scenario persona.");
  if (result.identity !== actorId)
    return answer(
      "FAIL",
      "Gateway identity does not match the authenticated run persona.",
    );
  if (preset.availability !== "retained")
    return answer("NOT IMPLEMENTED", preset.availabilityReason);
  if (preset.id === "preset-rag-denied") {
    if (
      result.action !== "BLOCK" ||
      result.model_called !== false ||
      result.context_count !== 0 ||
      result.reason_code !== "AUTHORIZATION_DENIED"
    )
      return answer(
        "FAIL",
        "ACL denial requires BLOCK, no model call, zero context and AUTHORIZATION_DENIED.",
      );
    if (result.provider.toLowerCase().includes("mock"))
      return answer(
        "FAIL",
        "Mock execution cannot verify authorization denial.",
      );
    if (result.stages?.includes("llm"))
      return answer(
        "FAIL",
        "Authorization denial contradicts a completed LLM stage.",
      );
    if (
      !Array.isArray(result.stages) ||
      !["auth", "authorization"].every((stage) =>
        result.stages!.includes(stage),
      )
    )
      return answer(
        "NOT IMPLEMENTED",
        "Authentication and authorization stage evidence is missing.",
      );
    return answer(
      "PASS",
      "Authorization-only: Bob denied before retrieval; zero context and no LLM call.",
      "This does not verify NeMo, Laya, privacy, the real LLM or output inspection.",
    );
  }
  if (result.provider.toLowerCase().includes("mock"))
    return answer(
      "FAIL",
      "Mock provider cannot verify live pipeline behavior.",
    );
  const unavailable = presetUnavailable(preset, status, actorId);
  if (unavailable) return answer("NOT IMPLEMENTED", unavailable);
  const failures: string[] = [];
  if (result.action !== preset.expectedAction)
    failures.push(
      `Expected ${preset.expectedAction}; received ${result.action}.`,
    );
  if (result.model_called !== preset.expectedModelCalled)
    failures.push("Model invocation differs from the scenario expectation.");
  if (!result.model_called && result.context_count !== 0)
    failures.push("Prevented scenario exposed context.");
  if (preset.id === "preset-rag-authorized" && result.context_count < 1)
    failures.push("Authorized retrieval produced no context.");
  if (result.model_called && !result.provider.trim())
    failures.push("Real model provider is missing.");
  const compact = (text: string) => text.replace(/[\s-]/g, "").toLowerCase();
  for (const value of preset.protectedValues) {
    if (compact(result.response).includes(compact(value)))
      failures.push(
        "Protected synthetic fixture appears in the released output.",
      );
    if (
      result.sanitized_prompt &&
      compact(result.sanitized_prompt).includes(compact(value))
    )
      failures.push(
        "Protected synthetic fixture remains in the sanitized input preview.",
      );
  }
  if (preset.expectedAction === "MASK" && !result.sanitized_prompt)
    failures.push("Input masking has no sanitized preview evidence.");
  if (failures.length) return answer("FAIL", ...failures);
  if (
    !Array.isArray(result.stages) ||
    !result.stages.every((stage) => typeof stage === "string")
  )
    return answer(
      "NOT IMPLEMENTED",
      "Completed-stage evidence is unavailable.",
    );
  const missing = preset.requiredStages.filter(
    (stage) => !result.stages!.includes(stage),
  );
  if (missing.length)
    return answer(
      "NOT IMPLEMENTED",
      `Required completed-stage evidence missing: ${missing.join(", ")}.`,
    );
  if (preset.assertionDirection === "output")
    return answer(
      "NOT IMPLEMENTED",
      "Output leakage requires a controlled generated-output fixture, separate from input masking.",
    );
  return answer(
    "PASS",
    `${preset.assertionDirection} contract assertions passed for ${actorId}.`,
    "Server-reported stage evidence; outbound payload and audit storage are not independently inspected by this UI.",
  );
}

export function writePresetHandoff(
  presetId: string,
  storage: Pick<Storage, "setItem">,
): void {
  storage.setItem(
    "aegis-selected-preset",
    JSON.stringify({ preset_id: presetId }),
  );
}

export function readPresetHandoff(
  storage: Pick<Storage, "getItem" | "removeItem">,
  routePresetId?: unknown,
): DemoPreset | null {
  const value = storage.getItem("aegis-selected-preset");
  storage.removeItem("aegis-selected-preset");
  if (typeof routePresetId === "string") {
    return FEATURE_PRESETS.find((preset) => preset.id === routePresetId && preset.availability !== "out-of-scope") || null;
  }
  if (!value) return null;
  try {
    const record: unknown = JSON.parse(value);
    if (
      !record ||
      typeof record !== "object" ||
      !("preset_id" in record) ||
      typeof record.preset_id !== "string"
    )
      return null;
    return (
      FEATURE_PRESETS.find(
        (preset) =>
          preset.id === record.preset_id &&
          preset.availability !== "out-of-scope",
      ) || null
    );
  } catch {
    return null;
  }
}

export function safeDemoEvidence(value: unknown, preset: DemoPreset): string {
  if (typeof value !== "string") return "not reported";
  const compact = (text: string) => text.replace(/[\s-]/g, "").toLowerCase();
  if (
    preset.protectedValues.some((secret) =>
      compact(value).includes(compact(secret)),
    )
  )
    return "Withheld: evidence contains a protected synthetic fixture.";
  return value || "not reported";
}

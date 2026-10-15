import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Play,
  MessageSquare,
  Terminal,
  Shield,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
import {
  FEATURE_PRESETS,
  PRESET_CATEGORIES,
  DEMO_TOUR_STEPS,
  type DemoPreset,
} from "../presets";
import { api, type User } from "../main";
import {
  presetUnavailable,
  verifyDemo,
  writePresetHandoff,
  safeDemoEvidence,
  readinessError,
  presetExecutionBlocked,
  type DemoResult,
  type DemoStatus,
} from "../demoVerification";

interface FeatureDemosProps {
  user: User;
  onSwitchPersona: (username: string) => Promise<User>;
}
type Run = { actor: string; result?: DemoResult; error?: string };
const display = (value: unknown) =>
  ["string", "number", "boolean"].includes(typeof value)
    ? String(value)
    : "not reported";
const displayList = (value: unknown) =>
  Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value.join(", ") || "none"
    : "not reported";

export function FeatureDemos({ user, onSwitchPersona }: FeatureDemosProps) {
  const navigate = useNavigate();
  const [category, setCategory] = useState("ALL");
  const [query, setQuery] = useState("");
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [switchError, setSwitchError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, Run>>({});
  // Also lock two clicks that occur before React rerenders.
  const lock = useRef(false);
  const generation = useRef({ id: user.id, version: 0 });
  if (generation.current.id !== user.id)
    generation.current = {
      id: user.id,
      version: generation.current.version + 1,
    };
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [refresh, setRefresh] = useState(0);
  const [checkingReadiness, setCheckingReadiness] = useState(false);
  useEffect(() => { setRuns({}); }, [user.id]);
  useEffect(() => {
    let active = true;
    setCheckingReadiness(true);
    setStatusError("");
    setSwitchError("");
    api<DemoStatus>("/demo/status")
      .then((next) => {
        if (
          typeof next?.pipeline_ready !== "boolean" ||
          typeof next.demo_login_enabled !== "boolean" ||
          !["mock", "live"].includes(next.execution_mode) ||
          !Array.isArray(next.components) ||
          !next.components.every(
            (component) =>
              component &&
              typeof component.name === "string" &&
              typeof component.status === "string" &&
              typeof component.detail === "string",
          )
        )
          throw new Error("Invalid readiness response.");
        if (active) setStatus(next);
      })
      .catch((error: unknown) => {
        if (active)
          setStatusError(readinessError(error));
      })
      .finally(() => {
        if (active) setCheckingReadiness(false);
      });
    return () => {
      active = false;
    };
  }, [user.id, refresh]);

  const runPreset = async (preset: DemoPreset) => {
    if (lock.current || presetExecutionBlocked(preset, user.id)) return;
    lock.current = true;
    const version = generation.current.version;
    const actor = user.id;
    setBusy(preset.id);
    setRuns((old) => {
      const next = { ...old };
      delete next[preset.id];
      return next;
    });
    try {
      const result = await api<DemoResult>("/demos/run", {
        method: "POST",
        body: JSON.stringify({
          preset_id: preset.id,
          prompt: preset.prompt,
          ...(preset.document_id ? { document_id: preset.document_id } : {}),
        }),
      });
      if (mounted.current && version === generation.current.version)
        setRuns((old) => ({ ...old, [preset.id]: { actor, result } }));
    } catch {
      if (mounted.current && version === generation.current.version)
        setRuns((old) => ({
          ...old,
          [preset.id]: {
            actor,
            error:
              "ERROR: demo request failed. No live result was verified; retry or sign in again.",
          },
        }));
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(null);
    }
  };
  const switchPersona = async (username: string) => {
    if (lock.current || user.role !== "admin" || !status?.demo_login_enabled)
      return;
    lock.current = true;
    setBusy("persona");
    setSwitchError("");
    setRuns({});
    try {
      await onSwitchPersona(username);
    } catch {
      if (mounted.current)
        setSwitchError(
          "ERROR: persona switch was refused or failed. Sign in with the intended account.",
        );
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(null);
    }
  };
  const handoff = (preset: DemoPreset) => {
    if (lock.current || preset.availability === "out-of-scope") return;
    try {
      writePresetHandoff(preset.id, sessionStorage);
      navigate("/app/chat", { state: { preset_id: preset.id } });
    } catch {
      setSwitchError("ERROR: unable to transfer the preset to Secure Chat.");
    }
  };
  const current = DEMO_TOUR_STEPS[step];
  const tourPreset = FEATURE_PRESETS.find(
    (preset) => preset.id === current.presetId,
  )!;
  const tourUnavailable = presetUnavailable(tourPreset, status, user.id);
  const tourBlocked = presetExecutionBlocked(tourPreset, user.id);
  const filtered = FEATURE_PRESETS.filter(
    (preset) =>
      (category === "ALL" || preset.category === category) &&
      [preset.id, preset.code, preset.title, preset.summary]
        .join(" ")
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );

  return (
    <div className="demo-studio">
      <div className="page-head">
        <span className="section-kicker">FEATURE DEMONSTRATION STUDIO</span>
        <p>
          Architecture v2: NeMo + Laya → Python policy → privacy → ACL → real
          LLM → Regex + Presidio. All fixtures are synthetic. Historical cards
          remain visible with their scope limitations.
        </p>
      </div>
      <section className="panel" aria-label="Pipeline readiness">
        <h2>
          {statusError ? "Unable to check pipeline readiness" : !status ? "Checking pipeline readiness…" : status.pipeline_ready && status.execution_mode === "live"
            ? "Live pipeline reported ready"
            : "NOT IMPLEMENTED — full live pipeline unavailable"}
        </h2>
        <p>
          Execution mode: {status?.execution_mode || "unknown"}. Readiness alone
          is not a verification result. Authorization denial can be tested
          independently.
        </p>
        {status?.components.map((component) => (
          <p key={component.name}>
            {component.name}: {component.status} — {component.detail}
          </p>
        ))}
        {statusError && (
          <p role="alert" className="error">
            {statusError}
          </p>
        )}
        <button
          type="button"
          className="outline"
          disabled={busy !== null || checkingReadiness}
          onClick={() => setRefresh((value) => value + 1)}
        >
          {checkingReadiness ? "Checking readiness…" : "Refresh readiness"}
        </button>
      </section>
      <section className="demo-tour-banner">
        <div className="demo-tour-info">
          <span className="demo-tour-step-badge">
            Guided tour · {current.step}/{DEMO_TOUR_STEPS.length}
          </span>
          <h2>{current.title}</h2>
          <p>{current.focus}</p>
          <p>{tourUnavailable || "Ready for this scenario's assertions."}</p>
        </div>
        <div className="demo-tour-controls">
          <button
            type="button"
            className="demo-tour-btn primary"
            disabled={busy !== null || !!tourBlocked}
            onClick={() => {
              setCategory("ALL");
              setQuery("");
              void runPreset(tourPreset);
            }}
          >
            <Play size={14} /> Run this step
          </button>
          <button
            type="button"
            className="demo-tour-btn secondary"
            disabled={busy !== null || step === 0}
            onClick={() => setStep((value) => value - 1)}
          >
            <ArrowLeft size={13} /> Prev
          </button>
          <button
            type="button"
            className="demo-tour-btn secondary"
            disabled={busy !== null || step === DEMO_TOUR_STEPS.length - 1}
            onClick={() => setStep((value) => value + 1)}
          >
            Next <ArrowRight size={13} />
          </button>
        </div>
      </section>
      <section className="persona-bar">
        <div className="persona-current">
          Active identity: {user.name} ({user.id}, {user.role})
        </div>
        {user.role === "admin" && status?.demo_login_enabled ? (
          <div className="persona-switches">
            {["admin", "alice", "bob", "individual"].map((id) => (
              <button
                type="button"
                key={id}
                className="persona-pill-btn"
                disabled={busy !== null || user.id === id}
                onClick={() => void switchPersona(id)}
              >
                Switch to {id}
              </button>
            ))}
          </div>
        ) : (
          <p>
            To test another persona, sign out and sign in with that account.
            Demo switching requires an administrator and enabled demo login.
          </p>
        )}
        {switchError && (
          <p role="alert" className="error">
            {switchError}
          </p>
        )}
      </section>
      <div className="demo-filters-wrap">
        <div className="demo-category-pills">
          {PRESET_CATEGORIES.map((item) => (
            <button
              type="button"
              key={item.id}
              className={`demo-filter-pill ${category === item.id ? "active" : ""}`}
              onClick={() => setCategory(item.id)}
            >
              {item.label} (
              {item.id === "ALL"
                ? FEATURE_PRESETS.length
                : FEATURE_PRESETS.filter(
                    (preset) => preset.category === item.id,
                  ).length}
              )
            </button>
          ))}
        </div>
        <input
          aria-label="Search scenarios"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search scenario IDs or titles"
        />
      </div>
      <div className="preset-grid">
        {filtered.map((preset) => {
          const unavailable = presetUnavailable(preset, status, user.id);
          const blocked = presetExecutionBlocked(preset, user.id);
          const run =
            runs[preset.id]?.actor === user.id ? runs[preset.id] : undefined;
          const verification = run?.result
            ? verifyDemo(preset, run.result, status, run.actor)
            : null;
          return (
            <article
              key={preset.id}
              id={preset.id}
              className="preset-card-full"
            >
              <div className="preset-header">
                <div>
                  <div className="preset-badge-group">
                    <span className="preset-code-badge">{preset.code}</span>
                    <span className="badge">{preset.categoryLabel}</span>
                  </div>
                  <h3 className="preset-title">{preset.title}</h3>
                </div>
                <span className="badge" data-action={preset.expectedAction}>
                  Expected: {preset.expectedAction}
                </span>
              </div>
              <p className="preset-summary">{preset.summary}</p>
              <p>
                <code>{preset.id}</code> · {preset.assertionDirection}{" "}
                assertions · Persona: {preset.recommendedRoleName}
              </p>
              <p>POST /api/demos/run · no legacy /api/chat execution</p>
              <p className="preset-persona-recommendation">
                {unavailable || preset.availabilityReason}
              </p>
              <div className="preset-talking-box">
                <div className="preset-talking-header">
                  <Terminal size={12} /> Scenario assertions
                </div>
                <ul className="preset-talking-list">
                  {preset.talkingPoints.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </div>
              <details>
                <summary>Synthetic fixture and assertion limits</summary>
                <div className="preset-payload-box">
                  <div className="preset-payload-label">
                    Synthetic input fixture
                    {preset.document_id && (
                      <span> · Requested resource: {preset.document_id}</span>
                    )}
                  </div>
                  <p className="preset-payload-text">{preset.prompt}</p>
                </div>
                <p>
                  Required completed stages: {preset.requiredStages.join(", ")}
                </p>
                <p>
                  Stage records are server-reported evidence. The browser does
                  not independently inspect outbound payloads or audit storage.
                </p>
              </details>
              <div className="preset-actions">
                <button
                  type="button"
                  className="preset-run-btn"
                  disabled={busy !== null || !!blocked}
                  title={blocked || "Request an actual backend result; missing components will be reported."}
                  onClick={() => void runPreset(preset)}
                >
                  <Play size={13} />
                  {busy === preset.id ? "Running…" : "Run demonstration"}
                </button>
                <button
                  type="button"
                  className="preset-chat-btn"
                  disabled={
                    busy !== null || preset.availability === "out-of-scope"
                  }
                  onClick={() => handoff(preset)}
                >
                  <MessageSquare size={13} /> Open in Secure Chat
                </button>
              </div>
              {run?.error && (
                <p role="alert" className="error">
                  {run.error}
                </p>
              )}
              {verification && (
                <div className="preset-result-drawer" role="status">
                  <div
                    className={`verification-status-banner ${verification.status === "PASS" ? "pass" : "notice"}`}
                  >
                    <strong>{verification.status}</strong>
                  </div>
                  {verification.details.map((detail, index) => (
                    <p key={index}>{detail}</p>
                  ))}
                  <p>
                    Result ID: {display(run?.result?.id)} · Reason code:{" "}
                    {display(run?.result?.reason_code)}
                  </p>
                  <p>
                    Run persona: {run?.actor} · Gateway identity:{" "}
                    {display(run?.result?.identity)} · Provider:{" "}
                    {display(run?.result?.provider)}
                  </p>
                  <p>
                    Execution status: {display(run?.result?.execution_status)} ·
                    Action: {display(run?.result?.action)} · Model called:{" "}
                    {display(run?.result?.model_called)} · Context:{" "}
                    {display(run?.result?.context_count)}
                  </p>
                  <div className="preset-result-metrics">
                    <div className="preset-result-metric-item">
                      <small>Gateway action</small>
                      <strong>{display(run?.result?.action)}</strong>
                    </div>
                    <div className="preset-result-metric-item">
                      <small>Model invocation</small>
                      <strong>
                        {run?.result?.model_called === true
                          ? "Called"
                          : run?.result?.model_called === false
                            ? "Not called"
                            : "Unknown"}
                      </strong>
                    </div>
                    <div className="preset-result-metric-item">
                      <small>Context count</small>
                      <strong>{display(run?.result?.context_count)}</strong>
                    </div>
                    <div className="preset-result-metric-item">
                      <small>Latency</small>
                      <strong>
                        {typeof run?.result?.latency === "number" &&
                        Number.isFinite(run.result.latency)
                          ? `${run.result.latency} ms`
                          : "not reported"}
                      </strong>
                    </div>
                  </div>
                  <p>Reason: {safeDemoEvidence(run?.result?.reason, preset)}</p>
                  <div className="preset-findings-strip">
                    {Array.isArray(run?.result?.findings) &&
                      run.result.findings.map((finding, index) => (
                        <span className="preset-finding-chip" key={index}>
                          <Shield size={10} />
                          {safeDemoEvidence(finding?.kind, preset)} ·{" "}
                          {typeof finding?.confidence === "number"
                            ? finding.confidence
                            : "unknown"}{" "}
                          confidence (server scale)
                        </span>
                      ))}
                  </div>
                  <div className="preset-payload-label">
                    Sanitized input preview (not proof of transmission)
                  </div>
                  <div className="preset-sanitized-preview">
                    {safeDemoEvidence(run?.result?.sanitized_prompt, preset)}
                  </div>
                  <div className="preset-payload-label">Gateway response</div>
                  <div className="preset-sanitized-preview">
                    {safeDemoEvidence(run?.result?.response, preset)}
                  </div>
                  <p>Completed stages: {displayList(run?.result?.stages)}</p>
                  <p>
                    Missing components:{" "}
                    {displayList(run?.result?.missing_components)}
                  </p>
                </div>
              )}
            </article>
          );
        })}
      </div>
      {!filtered.length && <p>No scenarios match this filter.</p>}
    </div>
  );
}

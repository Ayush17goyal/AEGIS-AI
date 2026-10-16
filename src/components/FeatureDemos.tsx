import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Play,
  MessageSquare,
  Terminal,
  Shield,
  UserRound,
  KeyRound,
  ShieldAlert,
  FileText,
  LockKeyhole,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
import {
  FEATURE_PRESETS,
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

const PROTECTION_CHOICES = [
  { id: "PERSONAL", label: "Protect personal information", description: "Keep personal details private when using AI.", icon: UserRound },
  { id: "SECRETS", label: "Protect passwords and keys", description: "Stop passwords and secret keys from leaking.", icon: KeyRound },
  { id: "THREATS", label: "Stop malicious instructions", description: "Prevent people from tricking AI into breaking its rules.", icon: ShieldAlert },
  { id: "DOCUMENTS", label: "Protect documents", description: "Keep documents and AI answers safe.", icon: FileText },
  { id: "ACCESS", label: "Control access and approvals", description: "Make sure only authorized people can access protected information.", icon: LockKeyhole },
] as const;

const demoGroup = (preset: DemoPreset) => {
  if (["PII", "FINANCIAL"].includes(preset.category)) return "PERSONAL";
  if (preset.category === "SECRET") return "SECRETS";
  if (["RAG", "APPROVAL"].includes(preset.category)) return "ACCESS";
  if (preset.category === "OUTPUT" || preset.id === "preset-inj-indirect") return "DOCUMENTS";
  return "THREATS";
};

const FRIENDLY_TITLES: Record<string, string> = {
  "preset-aadhaar-valid": "Aadhaar Number Protection",
  "preset-aadhaar-unverified": "Unverified Identity Number Check",
  "preset-pan-tax": "PAN Number Protection",
  "preset-contact-pii": "Contact Information Protection",
  "preset-payment-card": "Payment Card Protection",
  "preset-banking-ifsc": "Banking Details Protection",
  "preset-secret-aws": "Cloud Credentials Protection",
  "preset-secret-openai": "API Key Protection",
  "preset-secret-db": "Database Password Protection",
  "preset-secret-rsa": "Private Key Protection",
  "preset-secret-bearer": "Access Token Protection",
  "preset-inj-override": "Instruction Override Protection",
  "preset-inj-persona": "Developer Mode Bypass Protection",
  "preset-inj-zerowidth": "Hidden Prompt Attack Protection",
  "preset-benign-edu": "Safe Security Question",
  "preset-inj-indirect": "Unsafe Document Instruction Protection",
  "preset-rag-authorized": "Authorized Document Access",
  "preset-rag-denied": "Unauthorized Document Access",
  "preset-approval-queue": "Confidential Content Approval",
  "preset-output-redact": "AI Response Protection",
};

const friendlyRisk = (preset: DemoPreset) => ({
  PII: "Prevents personal identity and contact information from being exposed to an AI model.",
  FINANCIAL: "Protects payment and banking information before an AI request is processed.",
  SECRET: "Stops passwords, keys, and access tokens from being shared with an AI provider.",
  INJECTION: preset.id === "preset-inj-indirect"
    ? "Stops hidden instructions inside a document from controlling the AI response."
    : "Stops instructions that try to bypass AI safety and security rules.",
  RAG: "Checks document permissions before any protected information is retrieved.",
  APPROVAL: "Keeps confidential information on hold until an authorized reviewer approves it.",
  OUTPUT: "Checks AI-generated responses before sensitive information is returned to the user.",
  BENIGN: "Shows that a legitimate security question can continue without a false alarm.",
}[preset.category]);

const friendlyExample = (preset: DemoPreset) => ({
  PII: "Example: Detect an identity, phone, or email value before it reaches the model.",
  FINANCIAL: "Example: Mask a card number or bank account before sending the request.",
  SECRET: "Example: Stop an API key, password, or private token before model access.",
  INJECTION: preset.id === "preset-inj-indirect"
    ? "Example: Ignore malicious instructions embedded inside a retrieved document."
    : "Example: Block a prompt that asks the AI to ignore its safety rules.",
  RAG: "Example: Allow or deny a document based on the signed-in user’s permission.",
  APPROVAL: "Example: Pause a confidential request until a reviewer decides.",
  OUTPUT: "Example: Remove sensitive information found in an AI-generated answer.",
  BENIGN: "Example: Allow a normal educational question about cybersecurity.",
}[preset.category]);

export function FeatureDemos({ user, onSwitchPersona }: FeatureDemosProps) {
  const navigate = useNavigate();
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [switchError, setSwitchError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, Run>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
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
  const filtered = selectedGroup
    ? FEATURE_PRESETS.filter((preset) => demoGroup(preset) === selectedGroup)
    : [];
  const activePreset = filtered.find((preset) => preset.id === selectedPresetId) || filtered[0];

  return (
    <div className="demo-studio">
      <div className="page-head">
        <div>
          <span className="section-kicker">FEATURE DEMOS</span>
          <h1>See AI GUARD in Action</h1>
          <p>Choose what you want to protect. We&apos;ll show you how AI GUARD helps.</p>
        </div>
      </div>
      <details className="demo-environment-details">
        <summary>Environment details and guided testing</summary>
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
              setSelectedGroup(demoGroup(tourPreset));
              setSelectedPresetId(tourPreset.id);
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
      </details>
      {!selectedGroup ? (
        <section className="protection-choices" aria-label="Choose what to protect">
          {PROTECTION_CHOICES.map((choice) => {
            const count = FEATURE_PRESETS.filter((preset) => demoGroup(preset) === choice.id).length;
            const Icon = choice.icon;
            return (
              <button
                type="button"
                className="protection-choice-card"
                key={choice.id}
                onClick={() => {
                  setSelectedGroup(choice.id);
                  setSelectedPresetId(null);
                }}
              >
                <span className="protection-choice-icon"><Icon size={25} /></span>
                <span className="protection-choice-copy">
                  <strong>{choice.label}</strong>
                  <span>{choice.description}</span>
                  <small>{count} demos available</small>
                </span>
                <ArrowRight size={18} />
              </button>
            );
          })}
        </section>
      ) : (
        <section className="demo-focus-view" aria-label="Selected protection category">
          <button type="button" className="demo-back-btn" onClick={() => {
            setSelectedGroup(null);
            setSelectedPresetId(null);
          }}>
            <ArrowLeft size={15} /> Back to protections
          </button>
          <div className="demo-focus-heading">
            <div>
              <span className="section-kicker">{PROTECTION_CHOICES.find((choice) => choice.id === selectedGroup)?.label}</span>
              <h2>Choose a demonstration</h2>
              <p>{PROTECTION_CHOICES.find((choice) => choice.id === selectedGroup)?.description}</p>
            </div>
            <span className="demo-count">{filtered.length} demos available</span>
          </div>
          <div className="demo-option-list">
            {filtered.map((preset) => (
              <button
                type="button"
                key={preset.id}
                className={`demo-option ${activePreset?.id === preset.id ? "active" : ""}`}
                onClick={() => setSelectedPresetId(preset.id)}
              >
                <span><strong>{FRIENDLY_TITLES[preset.id] || preset.title}</strong><small>{friendlyRisk(preset)}</small></span>
                <ArrowRight size={15} />
              </button>
            ))}
          </div>
        </section>
      )}
      {selectedGroup && activePreset && <div className="preset-grid demo-selected-grid">
        {[activePreset].map((preset) => {
          const unavailable = presetUnavailable(preset, status, user.id);
          const blocked = presetExecutionBlocked(preset, user.id);
          const run =
            runs[preset.id]?.actor === user.id ? runs[preset.id] : undefined;
          const verification = run?.result
            ? verifyDemo(preset, run.result, status, run.actor)
            : null;
          const cardStatus = run?.error
            ? { label: "Needs attention", tone: "failed" }
            : status?.execution_mode === "mock" && run?.result
              ? { label: "Simulation only", tone: "simulation" }
            : verification?.status === "PASS"
              ? { label: "Protected", tone: "passed" }
              : verification?.status === "FAIL" || verification?.status === "ERROR"
                ? { label: "Needs attention", tone: "failed" }
                : verification?.status === "NOT IMPLEMENTED" || blocked
                  ? { label: "Setup required", tone: "configuration" }
                  : status?.execution_mode === "mock"
                    ? { label: "Simulation only", tone: "simulation" }
                    : { label: "Ready to try", tone: "available" };
          const resultSummary = run?.error
            ? "The demo could not complete. No security result was verified."
            : status?.execution_mode === "mock" && run?.result
              ? "This result came from a simulation and does not confirm live protection."
            : verification?.status === "PASS"
                    ? "The security rule successfully applied the expected protection."
              : verification?.status === "FAIL"
                ? "The run did not match the expected security behavior."
                : verification?.status === "ERROR"
                  ? "The gateway returned an invalid or incomplete result."
                  : verification?.status === "NOT IMPLEMENTED"
                    ? "This demo needs configuration before it can run."
                    : "";
          return (
            <article
              key={preset.id}
              id={preset.id}
              className="preset-card-full"
            >
              <div className="preset-header">
                <span className="demo-friendly-category">{PROTECTION_CHOICES.find((item) => item.id === demoGroup(preset))?.label}</span>
                <span className={`demo-status-badge ${cardStatus.tone}`}>{cardStatus.label}</span>
              </div>
              <h3 className="preset-title">{FRIENDLY_TITLES[preset.id] || preset.title}</h3>
              <p className="preset-summary"><strong>What are we protecting?</strong> {friendlyRisk(preset)}</p>
              <p className="preset-example"><strong>What will AI GUARD do?</strong> {friendlyExample(preset)}</p>
              <div className="preset-primary-actions">
                <button
                  type="button"
                  className="preset-run-btn"
                  disabled={busy !== null || !!blocked}
                  title={blocked || "Run this demo using the configured gateway."}
                  onClick={() => void runPreset(preset)}
                >
                  <Play size={13} />
                  {busy === preset.id ? "Running…" : "Try it"}
                </button>
                <button
                  type="button"
                  className="preset-details-btn"
                  aria-expanded={!!expanded[preset.id]}
                  onClick={() => setExpanded((old) => ({ ...old, [preset.id]: !old[preset.id] }))}
                >
                  {expanded[preset.id] ? "Hide details" : "View details"}
                </button>
              </div>
              {busy === preset.id && <p className="demo-run-feedback" role="status">Running the security check…</p>}
              {resultSummary && <div className={`demo-result-summary ${cardStatus.tone}`} role="status"><strong>{cardStatus.label}</strong><span>{resultSummary}</span></div>}
              {expanded[preset.id] && <div className="preset-technical-content">
              <h4>Technical details</h4>
              <p>
                <code>{preset.id}</code> · {preset.assertionDirection}{" "}
                assertions · Persona: {preset.recommendedRoleName}
              </p>
              <p>
                Expected result: <strong>{preset.expectedAction}</strong> · Model call: {preset.expectedModelCalled ? "allowed after protection" : "stopped before model"}
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
              </div>}
            </article>
          );
        })}
      </div>}
    </div>
  );
}

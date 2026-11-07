import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Smile,
  Flame,
  HeartHandshake,
  Eye,
  Compass,
  Lightbulb,
  Heart,
  Sparkles,
  ArrowRight,
  Check,
  Shuffle,
  ChevronDown,
  FileText,
  AlertCircle,
} from "lucide-react";
import { api } from "./api";
import {
  StoryPreferences,
  HumanConnection,
  emptyCalibration,
  measuredCalibration,
  type MirrorPreference,
  type CalibrationDraft,
  type Calibration,
} from "./storytelling";
import "./ideas.css";
import { IdeaProgress, type GenerationProgress } from "./idea-progress";
import "./provider-progress.css";

type Genre = { id: string; name: string; description: string };
type Group = { id: string; name: string; description: string; genres: Genre[] };
type Selection = {
  human_mirror_preference?: MirrorPreference;
  voice_calibration?: Calibration | null;
  category_group_id: string;
  category_group: string;
  primary_genre_id: string;
  primary_genre: string;
  secondary_genre_id: string | null;
  genre_definition: string;
  surprise: boolean;
  taxonomy_version: string;
};
type Concept = {
  human_mirror?: any;
  idea_id: string;
  title: string;
  primary_genre_id: string;
  secondary_genre_id: string | null;
  logline: string;
  premise: string;
  opening_visual_hook: string;
  main_characters: string[];
  central_conflict: string;
  key_escalation: string;
  ending_direction: string;
  target_emotion: string;
  visual_feasibility: string;
  duration_seconds: number;
  quality_audit: { criterion: string; assessment: string; evidence: string }[];
};
type Batch = {
  id: string;
  number: number;
  run_id?: string;
  status: string;
  stage?: string;
  created: string;
  error?: string;
  validation_error?: string;
  provider?: string;
  generation_progress?: GenerationProgress;
  result?: { ideas: Concept[]; generated_at: string; provider: string };
};
type Session = {
  id: string;
  created: string;
  selection: Selection;
  batches: Batch[];
  selected_stories: { episode_id: number; title: string }[];
};
type Saved = Omit<Session, "batches" | "selected_stories"> & {
  batch_count: number;
};
const icons = [
  Search,
  Smile,
  Flame,
  HeartHandshake,
  Eye,
  Compass,
  Lightbulb,
  Heart,
];
const pending = (b: Batch) =>
  ["QUEUED", "RUNNING", "PREPARING", "AWAITING_MANUAL"].includes(b.status);
function stored() {
  try {
    return JSON.parse(
      localStorage.getItem("odd-frame-genre-selection-v2") || "{}",
    );
  } catch {
    return {};
  }
}

export function IdeasStudio({
  onSelected,
  legacyHandoff,
}: {
  onSelected: (eid: number, runId?: string) => void;
  legacyHandoff?: React.ReactNode;
}) {
  const client = useQueryClient();
  const [initial] = useState(stored);
  const { data: taxonomy, error: taxonomyError } = useQuery<{
    version: string;
    groups: Group[];
  }>({
    queryKey: ["story-genres"],
    queryFn: () => api("/genres"),
    staleTime: 60000,
  });
  const { data: sessions = [] } = useQuery<Saved[]>({
    queryKey: ["idea-sessions"],
    queryFn: () => api("/idea-sessions"),
  });
  const provider = useQuery<{ provider: string }>({
    queryKey: ["idea-provider"],
    queryFn: () => api("/settings"),
  });
  const [groupId, setGroupId] = useState<string>(initial.group || ""),
    [genreId, setGenreId] = useState<string>(initial.genre || ""),
    [secondary, setSecondary] = useState<string>(initial.secondary || ""),
    [sid, setSid] = useState<string>(initial.session || ""),
    [batchId, setBatchId] = useState<string>(initial.batch || "");
  const [mirrorPreference, setMirrorPreference] = useState<MirrorPreference>(
    initial.mirror || "automatic",
  );
  const [calibration, setCalibration] = useState<CalibrationDraft>(
    initial.calibration || emptyCalibration,
  );
  const [title, setTitle] = useState<string>(initial.title || ""),
    [premise, setPremise] = useState<string>(initial.premise || ""),
    [ownStory, setOwnStory] = useState(false),
    [results, setResults] = useState(Boolean(initial.session)),
    [error, setError] = useState(""),
    [importText, setImportText] = useState(""),
    [tick, setTick] = useState(Date.now());
  const [intent, setIntent] = useState<{
      kind: "ideas" | "custom";
      session: Session;
      key: string;
      warning?: string;
      provider: string;
    } | null>(null),
    [keepPremise, setKeepPremise] = useState(false);
  const cancelButton = useRef<HTMLButtonElement>(null),
    submitting = useRef(false),
    opener = useRef<HTMLElement | null>(null),
    preparingRef = useRef(false);
  const [preparing, setPreparing] = useState(false);
  const session = useQuery<Session>({
    queryKey: ["idea-session", sid],
    queryFn: () => api("/idea-sessions/" + sid),
    enabled: !!sid,
    refetchInterval: (q) =>
      q.state.data?.batches.some(pending) ? 1500 : false,
    retry: false,
  });
  useEffect(() => {
    localStorage.setItem(
      "odd-frame-genre-selection-v2",
      JSON.stringify({
        group: groupId,
        genre: genreId,
        secondary,
        session: sid,
        batch: batchId,
        title,
        premise,
        mirror: mirrorPreference,
        calibration,
      }),
    );
  }, [
    groupId,
    genreId,
    secondary,
    sid,
    batchId,
    title,
    premise,
    mirrorPreference,
    calibration,
  ]);
  useEffect(() => {
    if (session.data?.id !== sid) return;
    const s = session.data.selection;
    setGroupId(s.category_group_id);
    setGenreId(s.surprise ? "surprise" : s.primary_genre_id);
    setSecondary(s.secondary_genre_id || "");
    setMirrorPreference(s.human_mirror_preference || "automatic");
    setCalibration(
      s.voice_calibration
        ? {
            voice: s.voice_calibration.voice,
            words: String(s.voice_calibration.measured_words),
            seconds: String(s.voice_calibration.measured_seconds),
            source: s.voice_calibration.source,
            date: s.voice_calibration.observed_at.slice(0, 10),
          }
        : emptyCalibration,
    );
  }, [sid, session.data?.id]);
  const group = taxonomy?.groups.find((g) => g.id === groupId),
    genre = group?.genres.find((g) => g.id === genreId);
  const batches = session.data?.batches || [],
    batch = batches.find((b) => b.id === batchId) || batches.at(-1),
    active = batches.find(pending),
    choicesReady = !!group && !!genreId;
  useEffect(() => {
    if (!active || active.status === "AWAITING_MANUAL") return;
    setTick(Date.now());
    const timer = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active?.id, active?.status]);
  const create = useMutation({
    mutationFn: (body: unknown) => api("/idea-sessions", "POST", body),
  });
  const generate = useMutation({
    mutationFn: ({
      sessionId,
      key,
      expectedProvider,
    }: {
      sessionId: string;
      key: string;
      expectedProvider: string;
    }) =>
      api(`/idea-sessions/${sessionId}/batches`, "POST", {
        idempotency_key: key,
        expected_provider: expectedProvider,
      }),
  });
  const select = useMutation({
    mutationFn: (concept: Concept) =>
      api(`/idea-sessions/${sid}/batches/${batch!.id}/select`, "POST", {
        idea_id: concept.idea_id,
      }),
    onSuccess: (r) => onSelected(r.episode_id, r.run_id),
  });
  const custom = useMutation({
    mutationFn: (body: unknown) =>
      api(`/idea-sessions/${intent!.session.id}/custom`, "POST", body),
    onSuccess: (r) => onSelected(r.episode_id, r.run_id),
  });
  const importing = useMutation({
    mutationFn: () =>
      api(`/runs/${active!.run_id}/import`, "POST", JSON.parse(importText)),
    onSuccess: () => {
      setImportText("");
      client.invalidateQueries({ queryKey: ["idea-session", sid] });
      client.invalidateQueries({ queryKey: ["activity"] });
    },
  });
  const busy =
    preparing || create.isPending || generate.isPending || custom.isPending;

  function changeGroup(id: string) {
    setGroupId(id);
    setGenreId("");
    setSecondary("");
    setSid("");
    setBatchId("");
    setResults(false);
    setError("");
  }
  function changeGenre(id: string) {
    setGenreId(id);
    setSecondary("");
    setSid("");
    setBatchId("");
    setResults(false);
    setError("");
  }
  async function ensureSession() {
    if (session.data && sid === session.data.id) return session.data;
    const created: Session = await create.mutateAsync({
      category_group_id: groupId,
      primary_genre_id: genreId === "surprise" ? null : genreId,
      secondary_genre_id: secondary || null,
      surprise: genreId === "surprise",
      human_mirror_preference: mirrorPreference,
      voice_calibration: measuredCalibration(calibration),
    });
    setSid(created.id);
    client.setQueryData(["idea-session", created.id], created);
    client.invalidateQueries({ queryKey: ["idea-sessions"] });
    return created;
  }
  async function confirmAction(kind: "ideas" | "custom") {
    if (busy || preparingRef.current || !choicesReady) return;
    opener.current = document.activeElement as HTMLElement | null;
    preparingRef.current = true;
    setPreparing(true);
    setError("");
    setKeepPremise(false);
    try {
      const prepared = await ensureSession(),
        settings = await provider.refetch();
      if (!settings.data?.provider)
        throw new Error(
          "Wait for provider settings before confirming generation.",
        );
      const key = crypto.randomUUID();
      let warning: string | undefined;
      if (kind === "custom")
        warning =
          (
            await api(`/idea-sessions/${prepared.id}/custom/check`, "POST", {
              idempotency_key: key,
              title,
              premise,
            })
          ).warning || undefined;
      setIntent({
        kind,
        session: prepared,
        key,
        warning,
        provider: settings.data.provider,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      preparingRef.current = false;
      setPreparing(false);
    }
  }
  async function submit() {
    if (!intent || submitting.current || (intent.warning && !keepPremise))
      return;
    submitting.current = true;
    setError("");
    try {
      if (intent.kind === "ideas") {
        const r = await generate.mutateAsync({
          sessionId: intent.session.id,
          key: intent.key,
          expectedProvider: intent.provider,
        });
        setBatchId(r.batch_id);
        setResults(true);
        setIntent(null);
        client.invalidateQueries({
          queryKey: ["idea-session", intent.session.id],
        });
        client.invalidateQueries({ queryKey: ["idea-sessions"] });
        client.invalidateQueries({ queryKey: ["activity"] });
      } else {
        await custom.mutateAsync({
          idempotency_key: intent.key,
          title,
          premise,
          keep_premise: keepPremise,
          expected_provider: intent.provider,
        });
        setIntent(null);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      submitting.current = false;
    }
  }
  function restoreSession(id: string) {
    setSid(id);
    setBatchId("");
    setResults(true);
    setError("");
  }
  async function cancelGeneration() {
    if (!active?.run_id) return;
    try {
      await api(`/runs/${active.run_id}/cancel`, "POST");
      client.invalidateQueries({ queryKey: ["idea-session", sid] });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const elapsed = active
    ? Math.max(0, Math.floor((tick - Date.parse(active.created)) / 1000))
    : 0;
  return (
    <div className="genre-studio">
      <div className="genre-intro">
        <span className="eyebrow gold">ORIGINAL STORIES. DISTINCT WORLDS.</span>
        <p>Start with a world, a feeling, or a question.</p>
      </div>
      {error && (
        <p className="genre-error" role="alert">
          <AlertCircle size={18} />
          {error}
        </p>
      )}
      {taxonomyError && (
        <p role="alert">
          Genre definitions could not load: {taxonomyError.message}
        </p>
      )}
      {sessions.length > 0 && (
        <label className="genre-history-label">
          Saved story sessions
          <select
            aria-label="Saved story sessions"
            value={sid}
            onChange={(e) => restoreSession(e.target.value)}
          >
            <option value="">New selection</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.selection.primary_genre} · {s.batch_count} batches ·{" "}
                {new Date(s.created).toLocaleDateString()}
              </option>
            ))}
          </select>
        </label>
      )}
      {(!results || !sid) && (
        <>
          <div className="category-grid" aria-label="Story category groups">
            {taxonomy?.groups.map((g, i) => {
              const Icon = icons[i];
              return (
                <Button
                  variant="outline"
                  key={g.id}
                  className={
                    "category-card" + (groupId === g.id ? " selected" : "")
                  }
                  aria-pressed={groupId === g.id}
                  onClick={() => changeGroup(g.id)}
                >
                  <span className="category-icon">
                    <Icon size={23} />
                  </span>
                  <span className="category-title">{g.name}</span>
                  <span className="category-description">{g.description}</span>
                  <span className="category-count">
                    {g.genres.length}{" "}
                    {g.genres.length === 1 ? "genre" : "genres"}
                    {groupId === g.id && <Check size={17} />}
                  </span>
                </Button>
              );
            })}
          </div>
          {group && (
            <section className="genre-selection panel">
              <div className="genre-section-heading">
                <div>
                  <span className="eyebrow">YOUR STORY DIRECTION</span>
                  <h3>{group.name}</h3>
                </div>
                <span>{group.genres.length} genres to explore</span>
              </div>
              <div className="genre-options" aria-label="Specific story genres">
                {group.genres.map((g) => (
                  <Button
                    className={
                      "genre-option" + (genreId === g.id ? " selected" : "")
                    }
                    key={g.id}
                    aria-pressed={genreId === g.id}
                    onClick={() => changeGenre(g.id)}
                  >
                    {g.name}
                    {genreId === g.id && <Check size={16} />}
                  </Button>
                ))}
                <Button
                  className={
                    "genre-option surprise" +
                    (genreId === "surprise" ? " selected" : "")
                  }
                  aria-pressed={genreId === "surprise"}
                  onClick={() => changeGenre("surprise")}
                >
                  <Shuffle size={16} />
                  Surprise Me Within This Group
                </Button>
              </div>
              <p className="genre-definition">
                {genre?.description ||
                  (genreId === "surprise"
                    ? "We will choose one genre from this group and show it before you confirm. Further batches keep that same primary genre."
                    : "Choose the specific genre that should shape the story.")}
              </p>
              {genreId && (
                <details className="genre-secondary">
                  <summary>Optional mixed genre</summary>
                  <label>
                    Secondary genre
                    <select
                      aria-label="Secondary genre"
                      value={secondary}
                      onChange={(e) => {
                        setSecondary(e.target.value);
                        setSid("");
                      }}
                    >
                      <option value="">No secondary genre</option>
                      {taxonomy?.groups
                        .flatMap((g) => g.genres)
                        .filter((g) => g.id !== genreId)
                        .map((g) => (
                          <option key={g.id} value={g.id}>
                            {g.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <p>
                    The selected primary genre remains the main storytelling
                    promise.
                  </p>
                </details>
              )}
            </section>
          )}
          <section className="genre-next panel">
            <StoryPreferences
              value={mirrorPreference}
              onChange={setMirrorPreference}
              calibration={calibration}
              onCalibration={setCalibration}
              locked={!!sid}
            />
            <div>
              <h3>
                {ownStory
                  ? "Develop your own story"
                  : "Five fresh possibilities"}
              </h3>
              <p>
                {ownStory
                  ? "Keep your title and optional premise. The selected genre guides development."
                  : "Five complete concepts with different characters, conflicts and ending directions."}
              </p>
            </div>
            <div
              className="genre-mode"
              role="group"
              aria-label="Story starting point"
            >
              <Button
                className={!ownStory ? "active" : ""}
                onClick={() => setOwnStory(false)}
              >
                Discover ideas
              </Button>
              <Button
                className={ownStory ? "active" : ""}
                onClick={() => setOwnStory(true)}
              >
                I have my own story
              </Button>
            </div>
            {ownStory && (
              <div className="genre-custom">
                <label>
                  Working title
                  <Input
                    aria-label="Working title"
                    value={title}
                    maxLength={150}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="The Fox Who Waited"
                  />
                </label>
                <label>
                  Your story premise <span>(optional)</span>
                  <Textarea
                    aria-label="Your story premise"
                    value={premise}
                    maxLength={5000}
                    onChange={(e) => setPremise(e.target.value)}
                    rows={4}
                    placeholder="Tell us the story you want to develop, or start with just a title."
                  />
                </label>
              </div>
            )}
            <Button
              className="genre-generate"
              disabled={
                !choicesReady ||
                busy ||
                !!active ||
                (ownStory && title.trim().length < 3)
              }
              onClick={() => void confirmAction(ownStory ? "custom" : "ideas")}
            >
              <Sparkles size={18} />
              {busy
                ? "Preparing selection…"
                : ownStory
                  ? "Develop This Story"
                  : "Generate 5 Story Ideas"}
              <ArrowRight size={17} />
            </Button>
            {!choicesReady && (
              <small>Choose a category and a genre to continue.</small>
            )}
          </section>
        </>
      )}
      {sid && session.error && (
        <p className="genre-error" role="alert">
          This saved session could not load: {session.error.message}
          <Button
            onClick={() => {
              setSid("");
              setResults(false);
            }}
          >
            Choose a new session
          </Button>
        </p>
      )}
      {sid && active && (
        <section
          className="genre-job panel"
          aria-label="Idea generation progress"
        >
          <div>
            <strong>
              {active.status === "AWAITING_MANUAL"
                ? "Manual handoff ready"
                : active.status === "QUEUED"
                  ? "Idea batch queued"
                  : active.status === "PREPARING"
                    ? "Preparing category-specific request"
                    : active.generation_progress?.request_sent
                      ? "Generating five story concepts"
                      : "Preparing five story concepts"}
            </strong>
            <span>
              {active.status === "AWAITING_MANUAL"
                ? "No automatic AI execution"
                : `${Math.floor(elapsed / 60)}m ${elapsed % 60}s elapsed`}
            </span>
          </div>
          <p>
            {active.status === "AWAITING_MANUAL"
              ? "Download the full category-specific request, use your chosen AI tool, then import its JSON response below."
              : null}
          </p>
          {active.status !== "AWAITING_MANUAL" && (
            <IdeaProgress
              progress={active.generation_progress}
              status={active.status}
              stage={active.stage}
              now={tick}
            />
          )}
          {!error && active.validation_error && (
            <p className="genre-error" role="alert">
              Last import failed validation: {active.validation_error}
            </p>
          )}
          {active.status === "AWAITING_MANUAL" && (
            <>
              <a
                className="button secondary"
                href={`/api/runs/${active.run_id}/request`}
                download
              >
                <FileText size={16} />
                Download complete category request
              </a>
              <label>
                Structured idea response
                <Textarea
                  aria-label="Structured idea response"
                  rows={7}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder="Paste the complete JSON response matching this batch’s schema."
                />
              </label>
              <Button
                disabled={!importText.trim() || importing.isPending}
                onClick={() => {
                  setError("");
                  importing.mutate(undefined, {
                    onError: (e) => setError(e.message),
                  });
                }}
              >
                Validate & Import Five Ideas
              </Button>
            </>
          )}
          {["QUEUED", "RUNNING", "AWAITING_MANUAL"].includes(active.status) && (
            <Button
              variant="outline"
              className="secondary"
              onClick={() => void cancelGeneration()}
            >
              {active.status === "AWAITING_MANUAL"
                ? "Cancel manual request"
                : "Cancel generation"}
            </Button>
          )}
        </section>
      )}
      {sid && results && (
        <section className="genre-results">
          <div className="genre-results-header">
            <div>
              <span className="eyebrow gold">
                {session.data?.selection.category_group}
              </span>
              <h3>{session.data?.selection.primary_genre} story concepts</h3>
              <p>{session.data?.selection.genre_definition}</p>
            </div>
            <div className="genre-result-actions">
              <Button
                variant="outline"
                className="secondary"
                onClick={() => setResults(false)}
              >
                Change Genre
              </Button>
              <Button
                disabled={busy || !!active}
                onClick={() => void confirmAction("ideas")}
              >
                <Sparkles size={16} />
                Generate Another 5 Ideas
              </Button>
            </div>
          </div>
          {batches.length > 0 && (
            <label className="genre-batches">
              Generation history
              <select
                aria-label="Generation batch"
                value={batch?.id || ""}
                onChange={(e) => setBatchId(e.target.value)}
              >
                {batches.map((b) => (
                  <option value={b.id} key={b.id}>
                    Batch {b.number} · {b.status.replaceAll("_", " ")} ·{" "}
                    {new Date(b.created).toLocaleString()}
                  </option>
                ))}
              </select>
            </label>
          )}
          {batch?.error && (
            <p className="genre-error" role="alert">
              {batch.error}
              <Button
                variant="outline"
                className="secondary"
                onClick={() => void confirmAction("ideas")}
              >
                Review & Retry Five Ideas
              </Button>
            </p>
          )}
          {batch?.status === "SUCCEEDED" && batch.result && (
            <>
              <p className="genre-batch-caption">
                Batch {batch.number} · Five validated concepts ·{" "}
                {batch.result.provider} ·{" "}
                {new Date(batch.result.generated_at).toLocaleString()}
              </p>
              <div className="concept-grid">
                {batch.result.ideas.map((c, i) => (
                  <article className="concept-card panel" key={c.idea_id}>
                    <div className="concept-top">
                      <span className="concept-number">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="concept-genre">
                        {session.data?.selection.primary_genre}
                        {c.secondary_genre_id ? " · mixed genre" : ""}
                      </span>
                    </div>
                    <h3>{c.title}</h3>
                    <p className="concept-logline">{c.logline}</p>
                    <dl>
                      <div>
                        <dt>The Premise</dt>
                        <dd>{c.premise}</dd>
                      </div>
                      <div>
                        <dt>Opening Hook</dt>
                        <dd>{c.opening_visual_hook}</dd>
                      </div>
                      <div>
                        <dt>Why Viewers Keep Watching</dt>
                        <dd>{c.central_conflict}</dd>
                      </div>
                      <div>
                        <dt>Characters</dt>
                        <dd>{c.main_characters.join(" · ")}</dd>
                      </div>
                      <div>
                        <dt>Ending Direction</dt>
                        <dd>{c.ending_direction}</dd>
                      </div>
                    </dl>
                    <HumanConnection value={c.human_mirror} />
                    <details>
                      <summary>
                        View Full Concept <ChevronDown size={15} />
                      </summary>
                      <p>
                        <strong>Escalation:</strong> {c.key_escalation}
                      </p>
                      <p>
                        <strong>Target emotion:</strong> {c.target_emotion}
                      </p>
                      <p>
                        <strong>Visual feasibility:</strong>{" "}
                        {c.visual_feasibility}
                      </p>
                      <p>
                        <strong>Suggested duration:</strong> About{" "}
                        {c.duration_seconds} seconds; actual timing follows
                        narration.
                      </p>
                      <details>
                        <summary>Editorial assessments</summary>
                        <ul>
                          {c.quality_audit.map((a) => (
                            <li key={a.criterion}>
                              <strong>{a.criterion}:</strong> {a.evidence}
                            </li>
                          ))}
                        </ul>
                        <small>
                          Editorial judgments, not verified popularity or
                          audience scores.
                        </small>
                      </details>
                    </details>
                    <Button
                      className="concept-select"
                      disabled={select.isPending}
                      onClick={() =>
                        select.mutate(c, {
                          onError: (e) => setError(e.message),
                        })
                      }
                    >
                      Select This Story
                      <ArrowRight size={16} />
                    </Button>
                  </article>
                ))}
              </div>
              <p className="genre-footnote">
                Diversity checks compare premises, relationships and conflicts.
                They reduce repetition without guaranteeing exhaustive
                originality.
              </p>
            </>
          )}
          {!batch && !session.isPending && (
            <p>
              No idea batches yet. Confirm your selection to generate the first
              five.
            </p>
          )}
          {!!session.data?.selected_stories.length && (
            <details>
              <summary>Stories selected from this session</summary>
              {session.data.selected_stories.map((s) => (
                <Button
                  variant="outline"
                  className="secondary"
                  key={s.episode_id}
                  onClick={() => onSelected(s.episode_id)}
                >
                  {s.title} → Episode {s.episode_id}
                </Button>
              ))}
            </details>
          )}
        </section>
      )}
      {legacyHandoff && (
        <details className="genre-legacy">
          <summary>Existing manual handoffs and legacy requests</summary>
          {legacyHandoff}
        </details>
      )}
      {intent && (
        <Dialog
          open
          onOpenChange={(open) => {
            if (!open && !busy) setIntent(null);
          }}
        >
          <DialogContent
            className="genre-dialog sm:max-w-xl max-h-[90dvh] overflow-y-auto"
            showCloseButton={!busy}
            onOpenAutoFocus={(e) => {
              e.preventDefault();
              cancelButton.current?.focus();
            }}
            onCloseAutoFocus={(e) => {
              e.preventDefault();
              opener.current?.focus();
            }}
            onEscapeKeyDown={(e) => {
              if (busy) e.preventDefault();
            }}
            onInteractOutside={(e) => {
              if (busy) e.preventDefault();
            }}
          >
            <div className="genre-confirm-icon">
              <Sparkles size={24} />
            </div>
            <DialogTitle id="genre-confirm-title">
              {intent.kind === "ideas"
                ? `Ready to Explore ${intent.session.selection.primary_genre} Stories?`
                : `Develop “${title}”?`}
            </DialogTitle>
            <DialogDescription id="genre-confirm-description">
              {intent.kind === "ideas"
                ? `ODD FRAME will generate five original ${intent.session.selection.primary_genre} story concepts with strong visual hooks, meaningful conflicts, and distinct endings.`
                : "Develop this specific owner-supplied story, then continue to the existing script review and approval workflow."}
            </DialogDescription>
            <dl>
              <div>
                <dt>Main category</dt>
                <dd>{intent.session.selection.category_group}</dd>
              </div>
              <div>
                <dt>Primary genre</dt>
                <dd>
                  {intent.session.selection.primary_genre}
                  {intent.session.selection.surprise
                    ? " · chosen within your group"
                    : ""}
                </dd>
              </div>
              <div>
                <dt>
                  {intent.kind === "ideas" ? "Number of ideas" : "Next stage"}
                </dt>
                <dd>
                  {intent.kind === "ideas"
                    ? "5"
                    : "Script writing and internal review"}
                </dd>
              </div>
              <div>
                <dt>AI provider</dt>
                <dd>{intent.provider}</dd>
              </div>
            </dl>
            {intent.provider === "manual" && (
              <p className="genre-manual-note">
                Manual mode prepares a complete request for export. It does not
                run AI automatically.
              </p>
            )}
            {intent.warning && (
              <div className="genre-premise-warning">
                <p>{intent.warning}</p>
                <label>
                  <Input
                    type="checkbox"
                    checked={keepPremise}
                    onChange={(e) => setKeepPremise(e.target.checked)}
                  />
                  Keep My Premise exactly as supplied
                </label>
                <Button
                  className="text-button"
                  onClick={() => {
                    setIntent(null);
                    setResults(false);
                  }}
                >
                  Change Genre
                </Button>
              </div>
            )}
            {error && (
              <p className="genre-error" role="alert">
                {error}
              </p>
            )}
            <div className="genre-dialog-actions">
              <Button
                ref={cancelButton}
                className="secondary"
                disabled={busy}
                onClick={() => setIntent(null)}
              >
                Cancel
              </Button>
              <Button
                disabled={busy || (!!intent.warning && !keepPremise)}
                onClick={() => void submit()}
              >
                {busy
                  ? "Submitting…"
                  : intent.kind === "ideas"
                    ? "Confirm & Generate"
                    : "Confirm & Develop"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

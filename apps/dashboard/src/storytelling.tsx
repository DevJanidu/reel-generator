import { useEffect, useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

export type MirrorPreference =
  "automatic" | "encourage_when_natural" | "pure_entertainment";
export type Calibration = {
  voice: string;
  measured_words: number;
  measured_seconds: number;
  source: string;
  observed_at: string;
};
export type CalibrationDraft = {
  voice: string;
  words: string;
  seconds: string;
  source: string;
  date: string;
};
export const emptyCalibration: CalibrationDraft = {
  voice: "",
  words: "",
  seconds: "",
  source: "",
  date: new Date().toISOString().slice(0, 10),
};
export function measuredCalibration(
  draft: CalibrationDraft,
): Calibration | null {
  if (![draft.voice, draft.words, draft.seconds, draft.source].some(Boolean))
    return null;
  if (
    !draft.voice ||
    !draft.source ||
    !draft.date ||
    !Number.isInteger(Number(draft.words)) ||
    Number(draft.words) <= 0 ||
    !Number.isFinite(Number(draft.seconds)) ||
    Number(draft.seconds) <= 0
  )
    throw Error(
      "Complete the measured voice name, word count, seconds, source and observation date, or clear the optional sample.",
    );
  return {
    voice: draft.voice,
    measured_words: Number(draft.words),
    measured_seconds: Number(draft.seconds),
    source: draft.source,
    observed_at: draft.date,
  };
}
export function StoryPreferences({
  value,
  onChange,
  calibration,
  onCalibration,
  locked,
}: {
  value: MirrorPreference;
  onChange: (value: MirrorPreference) => void;
  calibration: CalibrationDraft;
  onCalibration: (value: CalibrationDraft) => void;
  locked: boolean;
}) {
  return (
    <Accordion type="single" collapsible className="mb-4">
      <AccordionItem value="story-preferences">
        <AccordionTrigger>Story preferences (optional)</AccordionTrigger>
        <AccordionContent className="space-y-4">
          <p>
            Retention-first craft, with a flexible 40–55 second pilot target.
            Genre and story needs come first.
          </p>
          <label className="grid gap-2">
            Human World Connection
            <Select
              value={value}
              onValueChange={(v) => onChange(v as MirrorPreference)}
              disabled={locked}
            >
              <SelectTrigger aria-label="Human World Connection">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="automatic">
                  Automatic (recommended)
                </SelectItem>
                <SelectItem value="encourage_when_natural">
                  Encourage when natural
                </SelectItem>
                <SelectItem value="pure_entertainment">
                  Pure entertainment — no human reflection
                </SelectItem>
              </SelectContent>
            </Select>
          </label>
          <p className="text-muted-foreground">
            No setting forces a moral. Pure entertainment still allows
            believable feelings and character choices.
          </p>
          {locked && (
            <p>
              These preferences are pinned to this session. Choose New selection
              to change them without altering earlier batches.
            </p>
          )}
          <fieldset disabled={locked} className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-3">Measured voice sample (optional)</legend>
            {(
              [
                ["voice", "Voice name / ID"],
                ["words", "Measured sample words"],
                ["seconds", "Measured sample seconds"],
                ["source", "Sample file or evidence source"],
                ["date", "Observation date"],
              ] as const
            ).map(([key, label]) => (
              <label className="grid gap-2" key={key}>
                {label}
                <Input
                  aria-label={label}
                  type={
                    key === "date"
                      ? "date"
                      : key === "words" || key === "seconds"
                        ? "number"
                        : "text"
                  }
                  value={calibration[key]}
                  onChange={(e) =>
                    onCalibration({ ...calibration, [key]: e.target.value })
                  }
                />
              </label>
            ))}
          </fieldset>
          <p className="text-muted-foreground">
            Enter actual measured delivery from the selected voice. Without a
            sample, no speaking rate or word-budget duration is invented. Final
            timing follows uploaded narration/SRT.
          </p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
export function HumanConnection({ value }: { value?: any }) {
  if (!value) return null;
  if (value.mode === "none")
    return (
      <p className="text-sm text-muted-foreground">
        Entertainment-first story — no human-life parallel required.
      </p>
    );
  return (
    <Accordion type="single" collapsible>
      <AccordionItem value="connection">
        <AccordionTrigger>Human World Connection</AccordionTrigger>
        <AccordionContent className="space-y-2">
          <p>{value.real_world_connection}</p>
          <p>{value.storytelling_approach}</p>
          <p className="text-muted-foreground">{value.reason}</p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
export function RetentionAuditPanel({
  script,
  narration,
}: {
  script: any;
  narration: string;
}) {
  const [digest, setDigest] = useState("");
  useEffect(() => {
    let current = true;
    setDigest("");
    void crypto.subtle
      .digest("SHA-256", new TextEncoder().encode(narration))
      .then((b) => {
        if (current)
          setDigest(
            Array.from(new Uint8Array(b))
              .map((n) => n.toString(16).padStart(2, "0"))
              .join(""),
          );
      });
    return () => {
      current = false;
    };
  }, [narration]);
  const audit = script?.retention_audit;
  if (!audit)
    return (
      <p className="muted">
        No structured retention audit is recorded for this draft. Historical
        scripts are preserved; no review is inferred.
      </p>
    );
  const current = digest && digest === script._review_narration_sha256;
  return (
    <Card className="my-5" role="region" aria-label="Retention Audit">
      <CardHeader>
        <CardTitle>Retention Audit</CardTitle>
        <CardDescription>
          Editorial assessment — not Facebook performance data or a retention
          guarantee.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p role="status">
          {!digest
            ? "Checking reviewed wording…"
            : current
              ? "Notes match the reviewed narration."
              : "Narration has changed or review evidence is unavailable. These notes are historical; check logic, continuity and payoff against your edits before approving."}
        </p>
        <p className="text-muted-foreground">
          {
            audit.logic_checks.filter((v: any) => v.assessment === "warning")
              .length
          }{" "}
          logic/continuity warnings reported. Review the checks below; these are
          editorial observations, not machine proof.
        </p>
        <dl className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["Opening hook", audit.opening_hook],
              ["Early stakes", audit.early_stakes],
              ["Main conflict", audit.main_conflict],
              ["Story promise", audit.story_promise],
              [
                "First meaningful discovery",
                audit.first_meaningful_discovery ||
                  "Not required for this story",
              ],
              [
                "Major turning point",
                audit.major_turning_point || "Not required for this story",
              ],
              ["Main payoff", audit.main_payoff],
              ["Ending type", audit.ending_type],
            ] as const
          ).map(([label, text]) => (
            <div key={label}>
              <dt className="font-semibold">{label}</dt>
              <dd className="text-muted-foreground">{text}</dd>
            </div>
          ))}
        </dl>
        <p>
          <strong>Spoken duration: </strong>
          {script._voice_timing?.estimated_seconds && current
            ? `Approximately ${script._voice_timing.estimated_seconds}s from the supplied measured voice sample; provisional. `
            : ""}
          {audit.duration_note}
        </p>
        <Accordion type="multiple">
          <AccordionItem value="progression">
            <AccordionTrigger>
              Narrative progression and plot threads
            </AccordionTrigger>
            <AccordionContent className="space-y-3">
              <ul className="list-disc pl-5">
                {audit.narrative_progression.map((v: string, i: number) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
              {audit.plot_threads.map((v: any, i: number) => (
                <p key={i}>
                  <strong>{v.question}</strong> —{" "}
                  {v.handling.replaceAll("_", " ")}. {v.evidence}
                </p>
              ))}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="logic">
            <AccordionTrigger>Logic and continuity checks</AccordionTrigger>
            <AccordionContent className="space-y-3">
              {audit.logic_checks.map((v: any) => (
                <p key={v.domain}>
                  <strong>
                    {v.domain}: {v.assessment.replaceAll("_", " ")}
                  </strong>{" "}
                  — {v.evidence}
                </p>
              ))}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
        <HumanConnection value={script.human_mirror} />
      </CardContent>
    </Card>
  );
}

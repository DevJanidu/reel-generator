import { useState } from "react";
import { api } from "./api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";

type Data = Record<string, any>;
export function ContinuityPanel({ ep, fileURL, reload }: { ep: Data; fileURL: (path: string) => string; reload: () => Promise<unknown> }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [exportPath, setExportPath] = useState("");
  const [referenceFiles, setReferenceFiles] = useState<Record<string,string>>({});
  const plan = ep.data.package?.visual_continuity;
  const report = ep.continuity_report;
  async function act(path: string, body?: Data) {
    setBusy(true); setMessage("");
    try {
      const result = await api(`/episodes/${ep.id}/continuity/${path}`, "POST", body);
      if (result.path && path.startsWith("regenerate/")) setExportPath(result.path);
      setMessage(path.startsWith("regenerate/") ? "Scene queue prepared from the pinned plan. Download and import it into Flow." : path === "references" ? "Approved reference pinned. No attachment was sent to Flow." : "Owner review recorded for this image version.");
      await reload();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
    finally { setBusy(false); }
  }
  return <Card className="mb-6">
    <CardHeader><CardTitle>Visual continuity</CardTitle><CardDescription>
      {plan ? "Episode-specific canonical designs and story states. Text validation does not verify generated images." : "Historical package: its original creative version is retained. No structured visual plan has been adopted."}
    </CardDescription></CardHeader>
    <CardContent className="space-y-4">
      <p>Prompt validation: <Badge variant="outline">{report?.status ?? "NOT VALIDATED"}</Badge> · Flow queue 1.0 · References are not automatically attached.</p>
      <Accordion type="multiple">
        {plan && <AccordionItem value="bible"><AccordionTrigger>Visual Bible and references</AccordionTrigger><AccordionContent>
          {plan.bible.assets.map((a: Data) => <div key={a.id} className="mb-4"><strong>{a.name}</strong> <Badge variant="outline">{a.design_status}</Badge><p>{a.description}</p><p className="text-muted-foreground">{a.provenance}</p>
            {a.reference_ids.map((rid:string) => <div key={rid} className="my-2 flex flex-wrap gap-2">
              <label>Approved reference for {a.name}: <select aria-label={`Reference image for ${rid}`} value={referenceFiles[rid] ?? ""} onChange={e=>setReferenceFiles({...referenceFiles,[rid]:e.target.value})}>
                <option value="">Choose an imported image</option>
                {(ep.files ?? []).filter((f:string)=>/^05_assets\/images\/.*\.(png|jpg|jpeg|webp)$/i.test(f)).map((f:string)=><option key={f} value={f}>{f.split("/").at(-1)}</option>)}
              </select></label>
              <Button size="sm" variant="outline" disabled={busy || !referenceFiles[rid]} onClick={()=>void act("references",{reference_id:rid,path:referenceFiles[rid],approved:true})}>Pin approved reference</Button>
            </div>)}
          </div>)}
          <pre className="overflow-auto whitespace-pre-wrap">{JSON.stringify(ep.reference_manifest, null, 2)}</pre>
        </AccordionContent></AccordionItem>}
        <AccordionItem value="validation"><AccordionTrigger>Scene continuity and export readiness</AccordionTrigger><AccordionContent>
          <pre className="overflow-auto whitespace-pre-wrap">{JSON.stringify(report ?? { status: "NOT VALIDATED" }, null, 2)}</pre>
        </AccordionContent></AccordionItem>
        <AccordionItem value="review"><AccordionTrigger>Batch review in storyboard order</AccordionTrigger><AccordionContent>
          <p className="mb-4">Compare face, fur, costume, tail, architecture, scale, geography, props, lighting and story state. Check for text and panels. Review buttons record your inspection; no automated visual pass is claimed.</p>
          <div className="grid items-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(ep.data.package?.scenes ?? []).map((s: Data) => {
              const path = ep.files?.find((f: string) => new RegExp(`^05_assets/images/${s.scene_id}\\.(png|jpg|jpeg|webp)$`, "i").test(f));
              const review = ep.batch_review?.history?.filter((r: Data) => r.scene_id === s.scene_id).at(-1);
              return <Card key={s.scene_id}><CardHeader><CardTitle>{s.scene_id}</CardTitle><CardDescription>{s.narration_text}</CardDescription></CardHeader><CardContent className="space-y-3">
                {path ? <a href={fileURL(path)} target="_blank" rel="noreferrer"><img src={fileURL(path)} alt={`Generated image for ${s.scene_id}; requires visual review`} className="aspect-[9/16] w-full object-contain" /></a> : <p>No generated image imported.</p>}
                <p>Latest owner record: {review ? review.current_image_matches ? review.status : "STALE — image changed" : "UNREVIEWED"}{review ? " (applies to its recorded image hash)" : ""}</p>
                {path && <div className="flex flex-wrap gap-2">{["PASS", "WARNING", "REJECT"].map(status => <Button size="sm" variant="outline" disabled={busy} key={status} onClick={() => void act("review", { scene_id:s.scene_id, path, status, inspected:true })}>Reviewed: {status.toLowerCase()}</Button>)}</div>}
                {plan && <Button size="sm" variant="outline" disabled={busy} onClick={() => void act(`regenerate/${s.scene_id}`)}>Prepare scene regeneration</Button>}
              </CardContent></Card>;
            })}
          </div>
        </AccordionContent></AccordionItem>
      </Accordion>
      {message && <p role="status">{message}</p>}
      {exportPath && <a className="underline" href={fileURL(exportPath)} download>Download scene regeneration JSON</a>}
    </CardContent>
  </Card>;
}

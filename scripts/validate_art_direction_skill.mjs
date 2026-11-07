// Validate with the already installed YAML parser; no package installation.
import fs from "node:fs";
import crypto from "node:crypto";
import yaml from "js-yaml";

const manifest=JSON.parse(fs.readFileSync("brand/SKILLS_MANIFEST.json","utf8"));
const candidate=manifest.visual_art_direction.candidate;
const raw=fs.readFileSync(candidate.canonical_path),text=raw.toString("utf8");
const front=/^---\n([\s\S]*?)\n---/.exec(text);
if(!front)throw Error("Missing YAML frontmatter");
const data=yaml.load(front[1]);
const allowed=new Set(["name","description","license","allowed-tools","metadata"]);
if(!data || typeof data!=="object" || Object.keys(data).some(k=>!allowed.has(k)))throw Error("Unsupported frontmatter");
if(typeof data.name!=="string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(data.name) || data.name.length>64)throw Error("Invalid skill name");
if(typeof data.description!=="string" || data.description.length>1024 || /[<>]/.test(data.description))throw Error("Invalid description");
if(data.metadata.version!=="3.0.0" || data.metadata.status!=="ready-for-owner-approval")throw Error("Metadata mismatch");
if(/^\s*\[TODO:.*\]\s*$/m.test(text))throw Error("Unfinished scaffold");
for(let i=0;i<=13;i++)if(!new RegExp(`^## ${i}\\. `,"m").test(text))throw Error(`Missing complete section ${i}`);
const hash=bytes=>crypto.createHash("sha256").update(bytes).digest("hex");
const profile=fs.readFileSync(candidate.profile_path);
if(hash(raw)!==candidate.sha256 || raw.length!==candidate.byte_length || hash(profile)!==candidate.profile_sha256 || profile.length!==candidate.profile_byte_length)throw Error("Registry checksum/length mismatch");
console.log(JSON.stringify({status:"PASS",validator:"installed js-yaml plus skill structural/checksum checks",name:data.name,version:data.metadata.version,approval:manifest.visual_art_direction.approved?.status ?? "PENDING"}));

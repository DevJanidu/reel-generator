import { Badge } from "@/components/ui/badge";
export function statusTone(value: string) {
  const state = value.toUpperCase();
  if (
    [
      "COMPLETE",
      "SUCCEEDED",
      "LOADED",
      "VALIDATED",
      "READY",
      "DETECTED",
      "CONNECTED",
    ].includes(state)
  )
    return "success";
  if (
    /FAIL|ERROR/.test(state) ||
    ["MISSING", "INVALID", "UNAVAILABLE"].includes(state)
  )
    return "error";
  if (
    /BLOCK|WARN/.test(state) ||
    [
      "AWAITING_ASSETS",
      "AWAITING_APPROVAL",
      "AWAITING_MANUAL",
      "CANCELLED",
    ].includes(state)
  )
    return "warning";
  return "neutral";
}
export function JobStatus({ value }: { value: string }) {
  return (
    <Badge
      variant="outline"
      className="status-badge"
      data-tone={statusTone(value)}
    >
      {value === "ASSETS_BLOCKED" ? "NEEDS ASSETS" : value.replaceAll("_", " ")}
    </Badge>
  );
}

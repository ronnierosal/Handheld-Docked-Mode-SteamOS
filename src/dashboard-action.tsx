import { DialogButton } from "@decky/ui";
import type { DialogButtonProps } from "@decky/ui";
import { DashboardIcon } from "./quick-access-overview";

type DashboardActionProps = Pick<DialogButtonProps, "onClick" | "disabled"> & {
  title: string;
  description: string;
  icon: Parameters<typeof DashboardIcon>[0]["kind"];
  expanded?: boolean;
};

/** One native focus target; no Item label/action columns or detached icon row. */
export function DashboardAction({ title, description, icon, expanded, onClick, disabled }: DashboardActionProps) {
  return (
    <DialogButton onClick={onClick} disabled={disabled} aria-expanded={expanded}
      style={{ width: "100%", minWidth: 0, height: "auto", minHeight: 60,
        margin: 0, padding: "12px", boxSizing: "border-box", borderRadius: 14,
        textAlign: "left", whiteSpace: "normal" }}>
      <span style={{ display: "grid", gridTemplateColumns: "24px minmax(0, 1fr) 16px",
        alignItems: "center", gap: 10, width: "100%", minWidth: 0, boxSizing: "border-box" }}>
        <span style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <DashboardIcon kind={icon} />
        </span>
        <span style={{ display: "block", minWidth: 0, whiteSpace: "normal",
          wordBreak: "normal", overflowWrap: "normal", lineHeight: 1.4 }}>
          <span style={{ display: "block", fontSize: 14, fontWeight: 600 }}>{title}</span>
          <span style={{ display: "block", fontSize: 12, fontWeight: 400, marginTop: 3 }}>{description}</span>
        </span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
          style={{ transform: expanded ? "rotate(90deg)" : undefined }}>
          <path d="m9 5 7 7-7 7" />
        </svg>
      </span>
    </DialogButton>
  );
}

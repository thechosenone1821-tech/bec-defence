import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { RedTeamApp } from "@/components/features/red-team";

export const metadata: Metadata = { title: "Red Team · ARK OMNITEK" };

export default function RedTeamPage() {
  return (
    <ConsoleShell appId="red-team">
      <RedTeamApp />
    </ConsoleShell>
  );
}

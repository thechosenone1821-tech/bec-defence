import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { GovernanceApp } from "@/components/features/governance";

export const metadata: Metadata = { title: "Governance · ARK OMNITEK" };

export default function GovernancePage() {
  return (
    <ConsoleShell appId="governance">
      <GovernanceApp />
    </ConsoleShell>
  );
}

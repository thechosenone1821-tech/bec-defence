import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { CallScreenApp } from "@/components/features/call-screen";

export const metadata: Metadata = { title: "CALL SCREEN · ARK OMNITEK" };

export default function CallScreenPage() {
  return (
    <ConsoleShell appId="call-screen">
      <CallScreenApp />
    </ConsoleShell>
  );
}

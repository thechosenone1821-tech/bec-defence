import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { VigilApp } from "@/components/features/vigil";

export const metadata: Metadata = { title: "VIGIL · ARK OMNITEK" };

export default function VigilPage() {
  return (
    <ConsoleShell appId="vigil">
      <VigilApp />
    </ConsoleShell>
  );
}

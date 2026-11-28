import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { RingsApp } from "@/components/features/rings";

export const metadata: Metadata = { title: "Rings · ARK OMNITEK" };

export default function RingsPage() {
  return (
    <ConsoleShell appId="rings">
      <RingsApp />
    </ConsoleShell>
  );
}

import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { AttackLabApp } from "@/components/features/attack-lab";

export const metadata: Metadata = { title: "Attack Lab · ARK OMNITEK" };

export default function AttackLabPage() {
  return (
    <ConsoleShell appId="attack-lab">
      <AttackLabApp />
    </ConsoleShell>
  );
}

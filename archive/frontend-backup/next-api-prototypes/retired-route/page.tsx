import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { MayaApp } from "@/components/features/maya";

export const metadata: Metadata = { title: "MAYA · ARK OMNITEK" };

export default function MayaPage() {
  return (
    <ConsoleShell appId="maya">
      <MayaApp />
    </ConsoleShell>
  );
}

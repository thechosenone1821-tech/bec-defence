import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { CitizenSpineApp } from "@/components/features/citizen-spine";

export const metadata: Metadata = { title: "Citizen Spine · ARK OMNITEK" };

export default function CitizenSpinePage() {
  return (
    <ConsoleShell appId="citizen-spine">
      <CitizenSpineApp />
    </ConsoleShell>
  );
}

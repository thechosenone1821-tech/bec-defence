import type { Metadata } from "next";
import { ConsoleShell } from "@/components/shell/console-shell";
import { MessageGuardApp } from "@/components/features/message-guard";

export const metadata: Metadata = { title: "Message Guard · ARK OMNITEK" };

export default function MessageGuardPage() {
  return (
    <ConsoleShell appId="message-guard">
      <MessageGuardApp />
    </ConsoleShell>
  );
}

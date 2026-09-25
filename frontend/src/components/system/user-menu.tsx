"use client";

import { Menu } from "@base-ui/react/menu";
import { ChevronDown, LoaderCircle, LockKeyhole, LogOut, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { PrivacyDialog } from "@/components/system/privacy-dialog";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  const parts = name
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

/** Google profile photo, falling back to initials when there is none or it fails to load. */
function Avatar({
  photoUrl,
  name,
  className,
}: {
  photoUrl: string | null;
  name: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const base = cn("shrink-0 rounded-full ring-2 ring-card", className);
  if (photoUrl && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- Google profile photo, external host
      <img
        src={photoUrl}
        alt=""
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className={cn(base, "object-cover")}
      />
    );
  }
  return (
    <span
      className={cn(
        base,
        "flex items-center justify-center bg-primary font-semibold text-primary-foreground",
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

/**
 * The signed-in Google account: avatar, name and email, with a menu to sign out.
 * `compact` shows only the avatar (for tight headers). Renders nothing when sign-in is off.
 */
export function UserMenu({ compact = false }: { compact?: boolean }) {
  const { enabled, user, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  if (!enabled || !user) return null;

  const email = user.email ?? "";
  const name = user.displayName || email || "Your account";

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <>
      <Menu.Root>
        <Menu.Trigger
          aria-label={`Account: ${name}${email ? ` (${email})` : ""}`}
          className={cn(
            "flex shrink-0 items-center gap-2 rounded-full border bg-card py-1 pr-2 pl-1 text-left shadow-xs transition-colors outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 data-[popup-open]:bg-muted",
            compact && "pr-1",
          )}
        >
          <Avatar photoUrl={user.photoURL} name={name} className="size-7 text-[11px]" />
          {!compact && (
            <span className="hidden min-w-0 flex-col leading-tight sm:flex">
              <span className="max-w-44 truncate text-sm font-medium">{name}</span>
              {email && email !== name && (
                <span className="max-w-44 truncate text-xs text-muted-foreground">{email}</span>
              )}
            </span>
          )}
          <ChevronDown
            className={cn("size-3.5 text-muted-foreground", compact && "hidden")}
            aria-hidden
          />
        </Menu.Trigger>

        <Menu.Portal>
          <Menu.Positioner side="bottom" align="end" sideOffset={8} className="z-50">
            <Menu.Popup className="w-72 origin-(--transform-origin) rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-lg outline-none transition-[opacity,scale] data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0">
              <div className="flex items-center gap-3 px-2.5 pt-2 pb-3">
                <Avatar photoUrl={user.photoURL} name={name} className="size-11 text-sm" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{name}</p>
                  {email && (
                    <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
                      <Mail className="size-3 shrink-0" aria-hidden />
                      <span className="truncate">{email}</span>
                    </p>
                  )}
                </div>
              </div>
              <p className="mx-1 mb-1.5 flex items-start gap-2 rounded-lg bg-accent/60 px-2.5 py-2 text-xs text-muted-foreground">
                <LockKeyhole className="mt-px size-3.5 shrink-0 text-success" aria-hidden />
                Your documents are private to this Google account.
              </p>
              <Menu.Item
                onClick={() => setPrivacyOpen(true)}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-sm outline-none select-none data-[highlighted]:bg-muted"
              >
                <ShieldCheck className="size-4 text-muted-foreground" aria-hidden />
                Privacy &amp; activity
              </Menu.Item>
              <Menu.Separator className="my-1 h-px bg-border" />
              <Menu.Item
                onClick={() => void handleSignOut()}
                disabled={signingOut}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-danger outline-none select-none data-[disabled]:opacity-60 data-[highlighted]:bg-red-50"
              >
                {signingOut ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <LogOut className="size-4" aria-hidden />
                )}
                {signingOut ? "Signing out…" : "Sign out"}
              </Menu.Item>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>
      <PrivacyDialog open={privacyOpen} onOpenChange={setPrivacyOpen} />
    </>
  );
}

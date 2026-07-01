"use client";
/* Google Identity Services sign-in button (docs/23 §1, M7 §5).
   Loads the GSI script on mount, initialises with clientId, renders the button.
   The id_token from Google's credential_response is POSTed to our backend.
   Requires: NEXT_PUBLIC_GOOGLE_CLIENT_ID env var (rendered client-side only). */

import * as React from "react";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id:    string;
            callback:     (resp: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              theme?:     string;
              size?:      string;
              type?:      string;
              text?:      string;
              shape?:     string;
              logo_alignment?: string;
              width?:     number;
              locale?:    string;
            }
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface GoogleSignInButtonProps {
  clientId:  string;
  onSuccess: (idToken: string) => void;
  onError:   (message: string) => void;
}

export function GoogleSignInButton({ clientId, onSuccess, onError }: GoogleSignInButtonProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!clientId || typeof window === "undefined") return;

    function initButton() {
      if (!window.google || !containerRef.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback:  (resp) => {
          if (resp.credential) {
            onSuccess(resp.credential);
          } else {
            onError("Google sign-in did not return a credential.");
          }
        },
        cancel_on_tap_outside: true,
      });
      window.google.accounts.id.renderButton(containerRef.current, {
        theme:          "filled_black",
        size:           "large",
        type:           "standard",
        text:           "signin_with",
        shape:          "rectangular",
        logo_alignment: "left",
        width:          320,
        locale:         "en",
      });
    }

    if (window.google) {
      initButton();
      return;
    }

    /* Load GSI script if not already present */
    const existing = document.getElementById("gsi-script");
    if (existing) {
      existing.addEventListener("load", initButton);
      return;
    }
    const script    = document.createElement("script");
    script.id       = "gsi-script";
    script.src      = "https://accounts.google.com/gsi/client";
    script.async    = true;
    script.defer    = true;
    script.onload   = initButton;
    script.onerror  = () => onError("Failed to load Google sign-in script.");
    document.head.appendChild(script);
  }, [clientId, onSuccess, onError]);

  return (
    <div
      ref={containerRef}
      className="flex justify-center"
      aria-label="Sign in with Google"
    />
  );
}

"use client";

import { Thread } from "@/components/thread";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";
import { AppStateProvider } from "@/providers/AppState";
import { ArtifactProvider } from "@/components/thread/artifact";
import { Toaster } from "@/components/ui/sonner";
import React, { useState } from "react";
import { useAuth } from "@/providers/Auth";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { CyPlanAILogoSVG } from "@/components/icons/cyplanai";
import { ShieldCheck } from "lucide-react";

type AuthMode = "login" | "register";

function AuthScreen() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    username: "",
    password: "",
    email: "",
    name: "",
  });

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ username: form.username, password: form.password });
      } else {
        await register({
          username: form.username,
          password: form.password,
          email: form.email,
          name: form.name || form.username,
        });
      }
    } catch (error) {
      toast.error(mode === "login" ? "Sign-in failed" : "Sign-up failed", {
        description: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-background p-6 overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
      </div>
      
      <div className="relative w-full max-w-md rounded-2xl bg-card p-8 shadow-2xl border border-border">
        {/* Logo and header */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative flex items-center justify-center h-20 w-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 mb-5 ring-4 ring-primary/5">
            <CyPlanAILogoSVG width={48} height={48} />
          </div>
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <h1 className="text-3xl font-bold text-card-foreground">
              CyPlanAI
            </h1>
          </div>
          <h2 className="text-xl font-semibold text-card-foreground mb-2">
            {mode === "login" ? "Sign in" : "Create your account"}
          </h2>
          <p className="text-sm text-muted-foreground text-center max-w-sm">
            {mode === "login"
              ? "Enter your credentials to access CyPlanAI"
              : "Start building comprehensive cybersecurity plans with AI assistance"}
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={form.username}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, username: event.target.value }))
              }
              autoComplete="username"
              required
            />
          </div>

          {mode === "register" && (
            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, name: event.target.value }))
                }
                autoComplete="name"
              />
            </div>
          )}

          {mode === "register" && (
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, email: event.target.value }))
                }
                autoComplete="email"
                required
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <PasswordInput
              id="password"
              value={form.password}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, password: event.target.value }))
              }
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </div>

          <Button
            type="submit"
            className="w-full mt-6"
            disabled={submitting}
            size="lg"
          >
            {submitting
              ? "Submitting..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </Button>
        </form>

        <div className="mt-8 pt-6 border-t border-border text-center text-sm text-muted-foreground">
          {mode === "login" ? (
            <span>
              Don't have an account?{" "}
              <button
                type="button"
                className="text-primary hover:underline"
                onClick={() => setMode("register")}
              >
                Create one
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{" "}
              <button
                type="button"
                className="text-primary hover:underline"
                onClick={() => setMode("login")}
              >
                Sign in instead
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DemoPage(): React.ReactNode {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <Toaster />
        <AuthScreen />
      </>
    );
  }

  return (
    <React.Suspense fallback={<div>Loading (layout)...</div>}>
      <Toaster />
      <AppStateProvider>
        <ThreadProvider>
          <StreamProvider>
            <ArtifactProvider>
              <Thread />
            </ArtifactProvider>
          </StreamProvider>
        </ThreadProvider>
      </AppStateProvider>
    </React.Suspense>
  );
}

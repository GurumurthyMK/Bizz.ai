"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface AuthFormProps {
  mode: "login" | "register";
}

const copy = {
  login: {
    title: "Log in to Bizz AI",
    description: "Access your business intelligence workspace.",
    submit: "Log in",
    pending: "Logging in…",
    switchPrompt: "New to Bizz AI?",
    switchLabel: "Create an account",
    switchHref: "/register",
  },
  register: {
    title: "Create your account",
    description: "Register to access the Bizz AI workspace.",
    submit: "Create account",
    pending: "Creating account…",
    switchPrompt: "Already have an account?",
    switchLabel: "Log in",
    switchHref: "/login",
  },
} as const;

/** Login / registration form using the Bizz AI design system. */
function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const { user, isReady, login, register } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);
  const text = copy[mode];

  // Valid session but stale/absent cookie gate (e.g. expired token):
  // the middleware let us through on cookie absence, or the cookie died.
  React.useEffect(() => {
    if (isReady && user != null) {
      router.replace("/overview");
    }
  }, [isReady, user, router]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      if (mode === "login") {
        await login({ email: email.trim(), password });
      } else {
        await register({ email: email.trim(), password });
      }
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else {
        setError("Something went wrong. Check your connection and try again.");
      }
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{text.title}</CardTitle>
        <CardDescription>{text.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate={false}>
          {error != null && (
            <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm">
              {error}
            </p>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`${mode}-email`}>Email</Label>
            <Input
              id={`${mode}-email`}
              type="email"
              autoComplete={mode === "login" ? "email" : "new-email"}
              required
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={pending}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`${mode}-password`}>Password</Label>
            <Input
              id={`${mode}-password`}
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={8}
              placeholder={mode === "register" ? "At least 8 characters" : "Your password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={pending}
            />
          </div>
          <Button type="submit" disabled={pending} aria-busy={pending}>
            {pending ? text.pending : text.submit}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            {text.switchPrompt}{" "}
            <Link href={text.switchHref} className="font-medium text-foreground underline underline-offset-4">
              {text.switchLabel}
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

export { AuthForm };

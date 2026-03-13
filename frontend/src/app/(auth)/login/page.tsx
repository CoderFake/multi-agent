"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ThemeToggle } from "@/components/theme-toggle";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { TypewriterText } from "@/components/typewriter-text";
import * as authApi from "@/lib/auth";
import { api } from "@/lib/api-client";
import type { ApiError } from "@/lib/api-client";
import { Loader2, CircleAlert } from "lucide-react";

export default function LoginPage() {
  const t = useTranslations();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const result = await authApi.login({ email, password });
      api.resetExpired();
      if (result.must_change_password) {
        router.push("/change-password");
      } else {
        try {
          const me = await authApi.getMe();
          if (me.is_superuser) {
            router.push("/system/organizations");
          } else if (me.memberships?.length > 0) {
            router.push("/dashboard");
          } else {
            router.push("/dashboard");
          }
        } catch {
          router.push("/dashboard");
        }
      }
    } catch (err) {
      const apiErr = err as ApiError;
      const errorKey = apiErr.error_code || "UNKNOWN_ERROR";
      setError(t(`errors.${errorKey}`));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Top-right controls */}
      <div className="fixed top-4 right-4 flex items-center gap-2 z-10">
        <LocaleSwitcher />
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm">
        {/* Title with typewriter effect */}
        <div className="mb-8">
          <h1 className="font-serif text-3xl text-foreground">
            <TypewriterText
              text={"Agent CMS.\nPlease sign in to continue"}
              speed={40}
              startDelay={200}
            />
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            {error && (
              <div className="flex items-center justify-center gap-2 text-sm text-destructive">
                <CircleAlert className="size-4 shrink-0" />
                {error}
              </div>
            )}
            <Input
              id="email"
              type="email"
              placeholder={t("auth.email")}
              aria-label={t("auth.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              autoFocus
              autoComplete="email"
              className="h-12 rounded-full px-5"
            />
            <Input
              id="password"
              type="password"
              placeholder={t("auth.password")}
              aria-label={t("auth.password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              autoComplete="current-password"
              className="h-12 rounded-full px-5"
            />
          </div>

          <div className="space-y-4">
            <Button
              type="submit"
              className="h-12 w-full rounded-full bg-foreground text-background hover:bg-foreground/90"
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="animate-spin mr-2" />}
              {isLoading ? t("auth.loggingIn") : t("auth.loginButton")}
            </Button>

            {/* OR CONTINUE WITH divider */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                 {/* text */}
                </span>
              </div>
            </div>

            <p className="text-center text-sm text-muted-foreground pt-2">
              Multi-Agent CMS &copy; {new Date().getFullYear()}
            </p>
          </div>
        </form>
      </div>
    </>
  );
}


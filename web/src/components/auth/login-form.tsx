"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, CircleAlert } from "lucide-react";
import { toast } from "sonner";

import { signIn, signInWithGoogle } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TypewriterText } from "@/components/chat/typewriter-text";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await signIn(email, password);
      toast.success("Signed in successfully");
      router.push("/");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to sign in";
      // Firebase error codes → user-friendly messages
      if (message.includes("auth/invalid-credential") || message.includes("auth/wrong-password")) {
        setError("Invalid email or password");
      } else if (message.includes("auth/user-not-found")) {
        setError("No account found with this email");
      } else if (message.includes("auth/too-many-requests")) {
        setError("Too many attempts. Please try again later.");
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <div className="mb-6">
        <h1 className="font-serif text-3xl text-foreground">
          <TypewriterText
            text={"Agent.\nPlease sign in to continue"}
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
            placeholder="Email address"
            aria-label="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
            className="h-12 rounded-full px-5"
          />
          <Input
            id="password"
            type="password"
            placeholder="Password"
            aria-label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            className="h-12 rounded-full px-5"
          />
        </div>
        <div className="space-y-4">
          <Button
            type="submit"
            className="h-12 w-full rounded-full bg-foreground text-background hover:bg-foreground/90"
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="animate-spin" />}
            Sign in
          </Button>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Button
              variant="outline"
              className="h-12 w-full rounded-full px-0 border-gray-300"
              onClick={async () => {
                try {
                  setIsLoading(true);
                  await signInWithGoogle();
                  toast.success("Signed in with Google successfully");
                  router.push("/");
                } catch (err: unknown) {
                  const msg = err instanceof Error ? err.message : "Failed to sign in with Google";
                  toast.error(msg);
                } finally {
                  setIsLoading(false);
                }
              }}
              type="button"
              disabled={isLoading}
              title="Continue with Google"
            >
              <GoogleIcon className="size-5" />
            </Button>

            <Button
              variant="outline"
              className="h-12 w-full rounded-full px-0 border-gray-300"
              onClick={() => toast.info("Facebook login will be implemented soon")}
              type="button"
              disabled={isLoading}
              title="Continue with Facebook"
            >
              <FacebookIcon className="size-5" />
            </Button>

            <Button
              variant="outline"
              className="h-12 w-full rounded-full px-0 border-gray-300"
              onClick={() => toast.info("Apple login will be implemented soon")}
              type="button"
              disabled={isLoading}
              title="Continue with Apple"
            >
              <AppleIcon className="size-5" />
            </Button>
          </div>

          <p className="text-center text-sm text-muted-foreground pt-2">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium text-foreground hover:underline">
              Create account
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}

const GoogleIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" {...props}>
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    <path d="M1 1h22v22H1z" fill="none" />
  </svg>
);

const FacebookIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" {...props}>
    <path d="M22.675 0h-21.35C.6 0 0 .6 0 1.325v21.351C0 23.4.6 24 1.325 24H12.82v-9.294H9.692v-3.622h3.128V8.413c0-3.1 1.893-4.788 4.659-4.788 1.325 0 2.463.099 2.795.143v3.24l-1.918.001c-1.504 0-1.795.715-1.795 1.763v2.313h3.587l-.467 3.622h-3.12V24h6.116c.73 0 1.323-.6 1.323-1.324V1.325C24 .6 23.4 0 22.675 0z" fill="#1877F2" />
  </svg>
);

const AppleIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512" width="20" height="20" fill="currentColor" {...props}>
    <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 24 184.8 8 273.5q-9 62.8 17.1 117.2c12.9 27.6 29.7 49 54.3 49 22.5 0 36-14 65.6-14 30.6 0 43.1 14 66.8 14 26.6 0 46-24.5 59-45.7 16.3-26.5 22.8-52.1 23-53.5-5.1-1.5-34-11.8-35.1-71.8zM263.6 119.5c25.6-20.9 36.6-45.7 34-71.5-24.7 1.4-54.6 17.5-69.4 36.9-14.7 19.3-26.4 46.1-22.6 72.8 26.3 2 52.4-17.3 58-38.2z" />
  </svg>
);

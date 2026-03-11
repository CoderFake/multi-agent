import { redirect } from "next/navigation";
import { getAuthenticatedEmail } from "@/lib/auth";
import { FeedbackForm } from "@/components/feedback/feedback-form";

export default async function FeedbackPage() {
  const email = await getAuthenticatedEmail();

  if (!email) {
    redirect("/login");
  }

  return <FeedbackForm />;
}

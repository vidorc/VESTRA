import { redirect } from "next/navigation";

// Server component: the app is auth-gated on the client (token lives in
// localStorage), so the entry point just forwards to the dashboard, whose
// layout performs the client-side auth check.
export default function Home() {
  redirect("/dashboard");
}

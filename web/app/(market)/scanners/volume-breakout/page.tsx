/* Named route for /scanners/volume-breakout — delegates to the shared [slug] resolver */
import { redirect } from "next/navigation";
export default function Page() { redirect("/scanners/volume-breakout"); }

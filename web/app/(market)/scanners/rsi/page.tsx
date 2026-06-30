/* Named route for /scanners/rsi — delegates to the shared [slug] resolver */
import { redirect } from "next/navigation";
export default function Page() { redirect("/scanners/rsi"); }

import { createFileRoute } from "@tanstack/react-router"
import SOSSync from "../components/SOSSync"

export const Route = createFileRoute("/sync")({
  component: SOSSync,
})
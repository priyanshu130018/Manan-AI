import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/doc")({
  component: DocLayout,
});

function DocLayout() {
  return <Outlet />;
}

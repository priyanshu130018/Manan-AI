import { createFileRoute } from "@tanstack/react-router";
import { ChatPage } from "@/components/chat/chat-page";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Manan AI" },
      {
        name: "description",
        content: "Ask anything you want to learn.",
      },
    ],
  }),
  component: LandingRouteComponent,
});

function LandingRouteComponent() {
  return <ChatPage />;
}

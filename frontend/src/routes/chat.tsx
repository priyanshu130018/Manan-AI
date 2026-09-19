import { createFileRoute } from "@tanstack/react-router";
import { ChatPage } from "@/components/chat/chat-page";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Manan AI" },
      {
        name: "description",
        content: "Ask anything you want to learn.",
      },
    ],
  }),
  component: ChatRouteComponent,
});

function ChatRouteComponent() {
  return <ChatPage />;
}

import { createFileRoute } from "@tanstack/react-router";
import { ChatPage } from "@/components/chat/chat-page";

export const Route = createFileRoute("/chat/$chatNumber")({
  head: ({ params }) => ({
    meta: [
      { title: `Chat ${params.chatNumber} — Manan AI` },
      {
        name: "description",
        content: "Ask anything you want to learn.",
      },
    ],
  }),
  component: ChatNumberRoute,
});

function ChatNumberRoute() {
  const { chatNumber } = Route.useParams();
  return <ChatPage chatNumberParam={chatNumber} />;
}

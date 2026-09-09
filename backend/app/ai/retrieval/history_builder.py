class HistoryBuilder:
    def build(
        self,
        summary: str,
        history: list[dict[str, str]],
    ) -> str:
        lines: list[str] = []

        if summary:
            lines.append(
                "Conversation Summary:"
            )
            lines.append(summary)
            lines.append("")

        lines.append("Recent Messages:")

        for message in history:
            role = message["role"].capitalize()

            lines.append(
                f"{role}: {message['content']}"
            )

        return "\n".join(lines)
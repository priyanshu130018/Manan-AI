import re


class Parser:
    def parse(
        self,
        text: str,
    ) -> str:
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()
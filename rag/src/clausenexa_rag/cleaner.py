import re
import unicodedata


def clean_text(text: str) -> str:

    if not text:
        return ""

    # Normalize Unicode
    text = unicodedata.normalize(
        "NFKC",
        text
    )

    # Standardize line endings
    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Remove unwanted characters
    text = text.replace(
        "\x00",
        ""
    )

    text = text.replace(
        "\x0c",
        "\n"
    )

    text = text.replace(
        "\xa0",
        " "
    )

    # Normalize spaces
    lines = []

    for line in text.split("\n"):

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        )

        lines.append(
            line.strip()
        )

    text = "\n".join(lines)

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()
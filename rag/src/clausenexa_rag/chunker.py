import re


PAGE_PATTERN = re.compile(
    r"^\[PAGE\s+(\d+)\]$",
    re.IGNORECASE
)


PRINTED_PAGE_PATTERN = re.compile(
    r"^Page\s+\d+$",
    re.IGNORECASE
)


CLAUSE_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)+|\d+\.|[A-Z]\d+\.)\s+"
)


HEADING_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9\s&(),'/\-]{4,}$"
)


def _is_new_section(line: str) -> bool:

    return bool(
        CLAUSE_PATTERN.match(line)
        or HEADING_PATTERN.match(line)
    )


def _split_into_legal_units(
    text: str
) -> list[dict]:

    units = []

    current_lines = []
    current_pages = set()

    current_page = None


    def save_current_unit():

        nonlocal current_lines
        nonlocal current_pages

        if current_lines:

            content = " ".join(
                current_lines
            ).strip()

            if content:

                units.append({
                    "content": content,
                    "pages": sorted(
                        current_pages
                    )
                })

        current_lines = []
        current_pages = set()


    for raw_line in text.split("\n"):

        line = raw_line.strip()

        if not line:
            continue


        # ------------------------------
        # Page marker
        # ------------------------------

        page_match = PAGE_PATTERN.match(
            line
        )

        if page_match:

            current_page = int(
                page_match.group(1)
            )

            continue


        # Ignore printed "Page 1" etc.
        if PRINTED_PAGE_PATTERN.match(line):
            continue


        # ------------------------------
        # New legal section
        # ------------------------------

        if _is_new_section(line):

            save_current_unit()

            current_lines = [line]

            if current_page is not None:

                current_pages.add(
                    current_page
                )

            continue


        # ------------------------------
        # Continue current section
        # ------------------------------

        current_lines.append(line)

        if current_page is not None:

            current_pages.add(
                current_page
            )


    save_current_unit()

    return units


def _split_long_unit(
    unit: dict,
    max_chars: int
) -> list[dict]:

    text = unit["content"]

    if len(text) <= max_chars:
        return [unit]


    words = text.split()

    parts = []

    current_words = []
    current_length = 0


    for word in words:

        required_length = len(word)

        if current_words:
            required_length += 1


        if (
            current_words
            and
            current_length
            + required_length
            > max_chars
        ):

            parts.append({
                "content": " ".join(
                    current_words
                ),
                "pages": unit["pages"]
            })

            current_words = [word]

            current_length = len(word)

        else:

            current_words.append(word)

            current_length += (
                required_length
            )


    if current_words:

        parts.append({
            "content": " ".join(
                current_words
            ),
            "pages": unit["pages"]
        })


    return parts


def chunk_text(
    text: str,
    max_chars: int = 1800,
    overlap_units: int = 1
) -> list[dict]:

    if not text:
        return []


    legal_units = (
        _split_into_legal_units(text)
    )


    expanded_units = []

    for unit in legal_units:

        expanded_units.extend(
            _split_long_unit(
                unit,
                max_chars
            )
        )


    chunks = []

    current_units = []


    for unit in expanded_units:

        potential_units = (
            current_units + [unit]
        )


        potential_text = "\n\n".join(
            item["content"]
            for item in potential_units
        )


        if (
            current_units
            and
            len(potential_text) > max_chars
        ):

            chunk_content = "\n\n".join(
                item["content"]
                for item in current_units
            )


            pages = sorted({
                page
                for item in current_units
                for page in item["pages"]
            })


            chunks.append({
                "chunk_index": len(chunks),
                "content": chunk_content,
                "page_numbers": pages,
                "char_count": len(
                    chunk_content
                )
            })


            # Clause-aware overlap
            if overlap_units > 0:

                current_units = (
                    current_units[
                        -overlap_units:
                    ]
                )

            else:

                current_units = []


        current_units.append(unit)


    # Save final chunk
    if current_units:

        chunk_content = "\n\n".join(
            item["content"]
            for item in current_units
        )


        pages = sorted({
            page
            for item in current_units
            for page in item["pages"]
        })


        chunks.append({
            "chunk_index": len(chunks),
            "content": chunk_content,
            "page_numbers": pages,
            "char_count": len(
                chunk_content
            )
        })


    return chunks
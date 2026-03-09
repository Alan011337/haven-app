"""Local fallback for annotated_doc.Doc.

The upstream package can become unreadable in some local environments.
Keeping a tiny compatible shim in-repo prevents import hangs during gates.
"""


class Doc:
    def __init__(self, documentation: str, /) -> None:
        self.documentation = documentation

    def __repr__(self) -> str:
        return f"Doc({self.documentation!r})"

    def __hash__(self) -> int:
        return hash(self.documentation)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Doc):
            return NotImplemented
        return self.documentation == other.documentation

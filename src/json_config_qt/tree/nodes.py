import base64
import binascii
import enum
import re
import typing

JsonValue = typing.Any

COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
BINARY_MIN_LENGTH = 64


class Kind(enum.StrEnum):
    """The type of a JSON value as presented to the user."""

    DICT = "dict"
    LIST = "list"
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    COLOR = "color"
    BINARY = "binary"
    NULL = "null"


CONTAINER_KINDS = (Kind.DICT, Kind.LIST)
# Kinds the user can convert a value to.
SWITCHABLE_KINDS = (
    Kind.NULL,
    Kind.BOOL,
    Kind.INT,
    Kind.FLOAT,
    Kind.STR,
    Kind.COLOR,
    Kind.LIST,
    Kind.DICT,
)


def default_value(kind: Kind) -> JsonValue:
    """Return the default JSON value for *kind*."""
    return {
        Kind.DICT: dict,
        Kind.LIST: list,
        Kind.BOOL: lambda: False,
        Kind.INT: lambda: 0,
        Kind.FLOAT: lambda: 0.0,
        Kind.STR: str,
        Kind.COLOR: lambda: "#ffffff",
        Kind.BINARY: str,
        Kind.NULL: lambda: None,
    }[kind]()


def is_binary_string(text: str) -> bool:
    """Return whether *text* looks like an encoded binary blob (base64)."""
    if len(text) < BINARY_MIN_LENGTH or len(text) % 4:
        return False
    try:
        base64.b64decode(text, validate=True)
    except binascii.Error, ValueError:
        return False
    return True


def kind_of(value: JsonValue) -> Kind:
    """Classify a JSON value."""
    if value is None:
        return Kind.NULL
    if isinstance(value, bool):  # before int: bool is an int subclass
        return Kind.BOOL
    if isinstance(value, int):
        return Kind.INT
    if isinstance(value, float):
        return Kind.FLOAT
    if isinstance(value, str):
        if COLOR_RE.match(value):
            return Kind.COLOR
        if is_binary_string(value):
            return Kind.BINARY
        return Kind.STR
    if isinstance(value, dict):
        return Kind.DICT
    if isinstance(value, list):
        return Kind.LIST
    raise TypeError(f"Unsupported JSON value: {value!r}")


class JsonNode:
    """A node of the JSON tree: leaf holds a value, containers hold children."""

    def __init__(
        self,
        key: str | int | None,
        value: JsonValue = None,
        parent: JsonNode | None = None,
    ):
        """Initialize the node.

        Args:
            key (str | int | None): Dict key or list index; None for the root.
            value (JsonValue, optional): The value; containers get child nodes.
            parent (JsonNode | None, optional): The parent node.
        """
        self.key = key
        self.parent = parent
        self.children: list[JsonNode] = []
        self.value: JsonValue = None
        self.kind = Kind.NULL
        self.assign(value)

    @property
    def is_container(self) -> bool:
        """Return whether this node is a dict or a list."""
        return self.kind in CONTAINER_KINDS

    @property
    def row(self) -> int:
        """Return this node's position within its parent's children."""
        return self.parent.children.index(self) if self.parent else 0

    def assign(self, value: JsonValue) -> None:
        """Replace this node's content with *value* (rebuilding children)."""
        self.kind = kind_of(value)
        self.children = []
        self.value = None
        if isinstance(value, dict):
            self.children = [JsonNode(k, v, self) for k, v in value.items()]
        elif isinstance(value, list):
            self.children = [JsonNode(i, v, self) for i, v in enumerate(value)]
        else:
            self.value = value

    def renumber(self) -> None:
        """Re-index list children after an insertion or removal."""
        if self.kind is Kind.LIST:
            for index, child in enumerate(self.children):
                child.key = index

    def to_python(self) -> JsonValue:
        """Rebuild the plain JSON value of this subtree."""
        if self.kind is Kind.DICT:
            return {child.key: child.to_python() for child in self.children}
        if self.kind is Kind.LIST:
            return [child.to_python() for child in self.children]
        return self.value

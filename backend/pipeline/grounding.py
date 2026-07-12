"""Shared grounding helper: constrain LLM output to real block ids.

Used wherever an LLM must cite the blocks a piece of generated text is based
on (stage-3 title/summary generation, the chat answer strategy). Every
reference's ``block_ids`` is typed as an ``IntEnum`` of the ids actually
present in the input, so constrained decoding can only ground a reference in
a block that really is in the input -- the model cannot invent references.
"""

import enum
from typing import Any

from pydantic import BaseModel, create_model


def build_grounded_reference_model(valid_block_ids: list[int]) -> type[BaseModel]:
    """A `text` + `block_ids` model, `block_ids` constrained to `valid_block_ids`."""
    ValidBlockId = enum.IntEnum(
        "ValidBlockId", {f"id_{b_id}": b_id for b_id in valid_block_ids}
    )
    return create_model(
        "Reference",
        text=(str, ...),
        block_ids=(list[ValidBlockId], ...),
    )


def build_grounded_references_schema(
    valid_block_ids: list[int],
    *,
    extra_fields: dict[str, tuple[type, Any]] | None = None,
    model_name: str = "GroundedReferences",
) -> type[BaseModel]:
    """A schema with a `references: list[Reference]` field, block-id constrained.

    `extra_fields` are inserted *before* `references` (e.g. stage-3's `title`,
    which the model should fix before summarizing) and are passed through
    verbatim to `pydantic.create_model` as `(type, default)` tuples.
    """
    Reference = build_grounded_reference_model(valid_block_ids)
    fields: dict[str, Any] = dict(extra_fields or {})
    fields["references"] = (list[Reference], ...)
    return create_model(model_name, **fields)

"""``ModelInput`` and chunk types, faithful to ``tinker.types``.

``battery`` and the cookbook use the text path (``EncodedTextChunk``) via
``ModelInput.from_ints`` / ``to_ints``. The image chunk types
(``ImageChunk`` / ``ImageAssetPointerChunk``) and the ``ModelInputChunk``
discriminated union are reproduced too — not because we serve images (a spec
non-goal), but because ``tinker_cookbook.renderers`` references
``tinker.types.ImageChunk`` etc. in module-level annotations, so they must exist
for the cookbook to import. They carry no backend behavior here.
"""

from __future__ import annotations

import base64
from typing import List, Union

from pydantic import BaseModel, Field, field_serializer, field_validator
from typing_extensions import Annotated, Literal

__all__ = [
    "EncodedTextChunk",
    "ImageChunk",
    "ImageAssetPointerChunk",
    "ModelInputChunk",
    "ModelInput",
]


class EncodedTextChunk(BaseModel):
    tokens: List[int]
    type: Literal["encoded_text"] = "encoded_text"

    @property
    def length(self) -> int:
        return len(self.tokens)


class ImageChunk(BaseModel):
    """Inline image bytes. Present for cookbook-import compatibility only."""

    data: bytes
    format: Literal["png", "jpeg"]
    expected_tokens: int | None = None
    type: Literal["image"] = "image"

    @field_validator("data", mode="before")
    @classmethod
    def _validate_data(cls, value: Union[bytes, str]) -> bytes:
        if isinstance(value, str):
            return base64.b64decode(value)
        return value

    @field_serializer("data")
    def _serialize_data(self, value: bytes) -> str:
        return base64.b64encode(value).decode("utf-8")

    @property
    def length(self) -> int:
        if self.expected_tokens is None:
            raise ValueError("ImageChunk expected_tokens must be set to compute length")
        return self.expected_tokens


class ImageAssetPointerChunk(BaseModel):
    """Image-by-reference. Present for cookbook-import compatibility only."""

    format: Literal["png", "jpeg"]
    location: str
    expected_tokens: int | None = None
    type: Literal["image_asset_pointer"] = "image_asset_pointer"

    @property
    def length(self) -> int:
        if self.expected_tokens is None:
            raise ValueError("ImageAssetPointerChunk expected_tokens must be set to compute length")
        return self.expected_tokens


# Discriminated union on the ``type`` tag, matching the real SDK.
ModelInputChunk = Annotated[
    Union[EncodedTextChunk, ImageAssetPointerChunk, ImageChunk],
    Field(discriminator="type"),
]


class ModelInput(BaseModel):
    chunks: List[ModelInputChunk]

    @classmethod
    def from_ints(cls, tokens: List[int]) -> "ModelInput":
        return cls(chunks=[EncodedTextChunk(tokens=list(tokens))])

    def to_ints(self) -> List[int]:
        if not all(isinstance(c, EncodedTextChunk) for c in self.chunks):
            raise ValueError("to_ints only supported for EncodedTextChunk-only ModelInput")
        return [tok for chunk in self.chunks for tok in chunk.tokens]  # type: ignore[union-attr]

    @property
    def length(self) -> int:
        return sum(chunk.length for chunk in self.chunks)

    @classmethod
    def empty(cls) -> "ModelInput":
        return cls(chunks=[])

    def append(self, chunk: "ModelInputChunk") -> "ModelInput":
        return ModelInput(chunks=self.chunks + [chunk])

    def append_int(self, token: int) -> "ModelInput":
        return self.append(EncodedTextChunk(tokens=[token]))

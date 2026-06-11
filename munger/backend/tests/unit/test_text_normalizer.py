"""Parser-output normalization: formula image refs -> $...$, dead figures -> placeholders."""

import pytest

import app.services.text_normalizer as tn
from app.services.text_normalizer import normalize_extracted_text

pytestmark = pytest.mark.no_db


class TestFormulaImages:
    def test_latex_alt_becomes_inline_math(self):
        text = r"resolved with ![O(\log N)](page3_img1.png) messages"
        assert normalize_extracted_text(text) == r"resolved with $O(\log N)$ messages"

    def test_subscript_braces_count_as_latex(self):
        text = "value ![x_{i}](img.png) here"
        assert normalize_extracted_text(text) == "value $x_{i}$ here"

    def test_long_latex_becomes_block_math(self):
        formula = r"\sum_{i=1}^{N} \frac{\log N}{2} + \mathbb{E}[X_i] - \epsilon_{threshold}"
        assert len(formula) > 60
        text = f"![{formula}](img.png)"
        assert normalize_extracted_text(text) == f"\n$$\n{formula}\n$$\n"


class TestPlainImages:
    def test_plain_alt_becomes_figure_placeholder(self):
        text = "see ![Chord ring topology](fig2.png) for details"
        assert (
            normalize_extracted_text(text)
            == "see *[Figure: Chord ring topology]* for details"
        )

    def test_empty_alt_image_is_removed(self):
        assert normalize_extracted_text("before ![](img.png) after") == "before  after"


class TestPassThrough:
    def test_text_without_images_is_unchanged(self):
        text = "Plain paragraph with $existing$ math and [a link](http://x)."
        assert normalize_extracted_text(text) == text

    def test_error_falls_back_to_raw_text(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("replacement exploded")

        # _IMAGE_RE.sub resolves _replace_image from module globals at call
        # time, so patching the function makes the sub() call raise.
        monkeypatch.setattr(tn, "_replace_image", boom)
        assert normalize_extracted_text("has ![x](y.png) image") == "has ![x](y.png) image"

from typing import Any, Dict

from llama_index.llms.anthropic import Anthropic


class AnthropicNoTemperature(Anthropic):
    """
    Compatibility wrapper for Anthropic SDK versions whose
    Messages.create() endpoint does not accept `temperature`.

    Keeps the workaround inside this project rather than modifying
    installed LlamaIndex package files.
    """

    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        kwargs = super()._model_kwargs.copy()
        kwargs.pop("temperature", None)
        return kwargs
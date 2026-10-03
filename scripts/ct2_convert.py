"""ct2-transformers-converter, with one compatibility shim. Called by fetch_models.sh.

ctranslate2 4.8.2's converter calls `from_pretrained(..., dtype=...)`. transformers only
accepts `dtype` from releases that also refuse to torch.load a .bin checkpoint with
torch<2.6, and opus-mt-en-sw ships only a .bin. torch 2.2.2 is the last build for Intel
macOS. So we pin transformers 4.46.3 and rename the argument back to `torch_dtype`.
Nothing about the conversion itself changes.
"""
from ctranslate2.converters import transformers as ct2_transformers

_load_model = ct2_transformers.TransformersConverter.load_model


def _load_model_torch_dtype(self, model_class, model_name_or_path, **kwargs):
    if "dtype" in kwargs:
        kwargs["torch_dtype"] = kwargs.pop("dtype")
    return _load_model(self, model_class, model_name_or_path, **kwargs)


ct2_transformers.TransformersConverter.load_model = _load_model_torch_dtype

if __name__ == "__main__":
    ct2_transformers.main()

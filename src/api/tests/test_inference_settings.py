from django.conf import settings


def test_inference_toggle_settings_exist_with_defaults():
    # Defaults are empty strings: empty INFERENCE_LAMBDA_PYSPACER => legacy path.
    assert hasattr(settings, "INFERENCE_LAMBDA_PYSPACER")
    assert hasattr(settings, "INFERENCE_CLASSIFIER_VERSION")
    assert isinstance(settings.INFERENCE_LAMBDA_PYSPACER, str)
    assert isinstance(settings.INFERENCE_CLASSIFIER_VERSION, str)


def test_contract_package_importable():
    from mermaid_inference_contract import PyspacerRequest, PyspacerResponse, S3Location

    assert PyspacerRequest is not None
    assert PyspacerResponse is not None
    assert S3Location is not None

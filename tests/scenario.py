import pytest

from . import operation_tests

class Scenario:
    scenario_dir: str = ""
    test_pdf_extractions: bool = False
    test_pdf_to_text: bool = False
    test_code_to_amr: bool = False
    test_equations_to_amr: bool = False
    test_profile_dataset: bool = False
    test_profile_model: bool = False
        

def gen_test_scenario(scenario):
    @pytest.mark.resource(scenario.scenario_dir)
    class TestScenario:
        pass

    def add_test(name):
        enable_test = getattr(scenario, name)
        if enable_test:
            test = getattr(operation_tests, name)
            setattr(scenario, name, test)

    detectable_tests = [
        "test_pdf_extractions",
        "test_pdf_to_text",
        "test_code_to_amr",
        "test_equations_to_amr",
        "test_profile_dataset",
        "test_profile_model",
    ]
        
    for name in detectable_tests:
        add_test(name)

    return TestScenario
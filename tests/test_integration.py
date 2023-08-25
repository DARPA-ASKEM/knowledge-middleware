from .scenario import Scenario, gen_test_scenario


@gen_test_scenario
class TestBasic(Scenario):
    scenario_dir = "basic"
    test_pdf_extractions = True
    test_pdf_to_text = True
    test_code_to_amr = True
    test_equations_to_amr = True
    test_profile_dataset = True
    test_profile_model = True


    
@gen_test_scenario
class TestSidarthe(Scenario):
    scenario_dir = "sidarthe"
    test_profile_dataset = True
    test_profile_model = True

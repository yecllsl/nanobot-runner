from src.core.base.context import AppContextFactory


def test_training_load_analyzer_property_exists():
    context = AppContextFactory.create(allow_default=True)
    analyzer = context.training_load_analyzer
    assert analyzer is not None
    from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

    assert isinstance(analyzer, TrainingLoadAnalyzer)


def test_vdot_calculator_property_exists():
    context = AppContextFactory.create(allow_default=True)
    calculator = context.vdot_calculator
    assert calculator is not None
    from src.core.calculators.vdot_calculator import VDOTCalculator

    assert isinstance(calculator, VDOTCalculator)


def test_race_prediction_engine_property_exists():
    context = AppContextFactory.create(allow_default=True)
    engine = context.race_prediction_engine
    assert engine is not None
    from src.core.calculators.race_prediction import RacePredictionEngine

    assert isinstance(engine, RacePredictionEngine)


def test_injury_risk_analyzer_property_exists():
    context = AppContextFactory.create(allow_default=True)
    analyzer = context.injury_risk_analyzer
    assert analyzer is not None
    from src.core.calculators.injury_risk_analyzer import InjuryRiskAnalyzer

    assert isinstance(analyzer, InjuryRiskAnalyzer)


def test_prediction_engine_feature_engine_receives_all_dependencies():
    context = AppContextFactory.create(allow_default=True)
    engine = context.prediction_engine
    fe = engine._vdot_predictor._feature_engine
    assert fe._load_analyzer is not None
    assert fe._hrv_analyzer is not None
    assert fe._body_signal_engine is not None
    assert fe._vdot_calculator is not None


def test_prediction_engine_vdot_predictor_receives_race_engine():
    context = AppContextFactory.create(allow_default=True)
    engine = context.prediction_engine
    assert engine._vdot_predictor._race_engine is not None


def test_prediction_engine_race_predictor_receives_race_engine_and_body_signal():
    context = AppContextFactory.create(allow_default=True)
    engine = context.prediction_engine
    assert engine._race_predictor._race_engine is not None
    assert engine._race_predictor._body_signal_engine is not None


def test_prediction_engine_injury_predictor_receives_injury_analyzer():
    context = AppContextFactory.create(allow_default=True)
    engine = context.prediction_engine
    assert engine._injury_predictor._injury_analyzer is not None

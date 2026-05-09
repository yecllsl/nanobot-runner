from __future__ import annotations

import pytest

from src.core.body_signal.models import DataQuality
from src.core.prediction.models import (
    AcuteLoadRisk,
    BodySignalRisk,
    ChronicRisk,
    DataSufficiencyReport,
    InjuryLabel,
    InjuryReportResult,
    InjuryRiskPrediction,
    MLPredictionInfo,
    ModelManagementResult,
    ModelMetadata,
    ModelStatus,
    ModelTrainingResult,
    PaceSplit,
    PaceStrategy,
    PersonalizationInfo,
    PredictionRecord,
    PredictionStatusReport,
    RacePredictionResult,
    RiskFactor,
    RiskTimePoint,
    SufficiencyDimension,
    TrainingResponse,
    VDOTFactor,
    VDOTPrediction,
)


class TestVDOTFactor:
    def test_create(self):
        f = VDOTFactor(name="ctl_value", weight=0.35, direction="positive", value=52.3)
        assert f.name == "ctl_value"
        assert f.weight == 0.35
        assert f.direction == "positive"
        assert f.value == 52.3

    def test_to_dict(self):
        f = VDOTFactor(name="ctl_value", weight=0.35, direction="positive", value=52.3)
        d = f.to_dict()
        assert d == {
            "name": "ctl_value",
            "weight": 0.35,
            "direction": "positive",
            "value": 52.3,
        }

    def test_frozen(self):
        f = VDOTFactor(name="ctl_value", weight=0.35, direction="positive", value=52.3)
        with pytest.raises(AttributeError):
            f.name = "other"


class TestMLPredictionInfo:
    def test_create(self):
        info = MLPredictionInfo(
            model_type="gradient_boosting",
            training_samples=500,
            feature_count=12,
            shap_available=True,
            quantile_models=True,
        )
        assert info.model_type == "gradient_boosting"
        assert info.training_samples == 500
        assert info.quantile_models is True

    def test_to_dict(self):
        info = MLPredictionInfo(
            model_type="gradient_boosting",
            training_samples=500,
            feature_count=12,
            shap_available=True,
            quantile_models=True,
        )
        d = info.to_dict()
        assert d["model_type"] == "gradient_boosting"
        assert d["quantile_models"] is True


class TestVDOTPrediction:
    def test_ml_enhanced(self):
        pred = VDOTPrediction(
            current_vdot=45.2,
            predicted_vdot=46.8,
            prediction_days=30,
            confidence_interval=(45.5, 48.1),
            confidence=0.85,
            trend_slope=0.05,
            key_factors=[
                VDOTFactor(
                    name="ctl_value", weight=0.35, direction="positive", value=52.3
                )
            ],
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
            model_info=MLPredictionInfo(
                model_type="gradient_boosting",
                training_samples=500,
                feature_count=12,
                shap_available=True,
                quantile_models=True,
            ),
        )
        assert pred.prediction_type == "ml_enhanced"
        assert pred.model_info is not None

    def test_parametric_no_model_info(self):
        pred = VDOTPrediction(
            current_vdot=45.2,
            predicted_vdot=46.0,
            prediction_days=30,
            confidence_interval=(44.8, 47.2),
            confidence=0.7,
            trend_slope=0.03,
            key_factors=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="parametric",
            model_info=None,
        )
        assert pred.prediction_type == "parametric"
        assert pred.model_info is None

    def test_basic_prediction_type(self):
        pred = VDOTPrediction(
            current_vdot=45.2,
            predicted_vdot=45.5,
            prediction_days=30,
            confidence_interval=(44.0, 47.0),
            confidence=0.5,
            trend_slope=0.01,
            key_factors=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="basic",
            model_info=None,
        )
        assert pred.prediction_type == "basic"

    def test_to_dict(self):
        pred = VDOTPrediction(
            current_vdot=45.2,
            predicted_vdot=46.8,
            prediction_days=30,
            confidence_interval=(45.5, 48.1),
            confidence=0.85,
            trend_slope=0.05,
            key_factors=[],
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
            model_info=None,
        )
        d = pred.to_dict()
        assert d["current_vdot"] == 45.2
        assert d["confidence_interval"] == [45.5, 48.1]
        assert d["data_quality"] == "sufficient"


class TestPaceSplit:
    def test_create_and_to_dict(self):
        s = PaceSplit(segment="0-5km", pace="5'30\"/km", pace_seconds=330.0)
        assert s.segment == "0-5km"
        d = s.to_dict()
        assert d["segment"] == "0-5km"
        assert d["pace_seconds"] == 330.0


class TestPaceStrategy:
    def test_create_and_to_dict(self):
        splits = [PaceSplit(segment="0-5km", pace="5'30\"/km", pace_seconds=330.0)]
        ps = PaceStrategy(strategy_type="even", splits=splits)
        d = ps.to_dict()
        assert d["strategy_type"] == "even"
        assert len(d["splits"]) == 1


class TestPersonalizationInfo:
    def test_create_and_to_dict(self):
        pi = PersonalizationInfo(
            runner_type="endurance",
            riegel_exponent=1.08,
            correction_factor=0.98,
            race_samples_count=5,
            pre_race_adjustment=0.03,
        )
        d = pi.to_dict()
        assert d["runner_type"] == "endurance"
        assert d["riegel_exponent"] == 1.08


class TestRacePredictionResult:
    def test_personalized(self):
        r = RacePredictionResult(
            distance_km=42.195,
            predicted_time="3:45:00",
            predicted_time_seconds=13500.0,
            confidence=0.8,
            best_case="3:35:00",
            worst_case="3:55:00",
            predicted_vdot=46.5,
            pace_strategy=PaceStrategy(strategy_type="even", splits=[]),
            prediction_type="personalized",
            personalization_info=PersonalizationInfo(
                runner_type="endurance",
                riegel_exponent=1.08,
                correction_factor=0.98,
                race_samples_count=5,
                pre_race_adjustment=0.03,
            ),
        )
        assert r.prediction_type == "personalized"
        assert r.personalization_info is not None

    def test_standard_no_optional(self):
        r = RacePredictionResult(
            distance_km=42.195,
            predicted_time="3:50:00",
            predicted_time_seconds=13800.0,
            confidence=0.6,
            best_case="3:40:00",
            worst_case="4:00:00",
            predicted_vdot=45.0,
            pace_strategy=None,
            prediction_type="standard",
            personalization_info=None,
        )
        assert r.prediction_type == "standard"
        assert r.pace_strategy is None

    def test_to_dict(self):
        r = RacePredictionResult(
            distance_km=42.195,
            predicted_time="3:45:00",
            predicted_time_seconds=13500.0,
            confidence=0.8,
            best_case="3:35:00",
            worst_case="3:55:00",
            predicted_vdot=46.5,
            pace_strategy=None,
            prediction_type="personalized",
            personalization_info=None,
        )
        d = r.to_dict()
        assert d["distance_km"] == 42.195


class TestRiskTimePoint:
    def test_create_and_to_dict(self):
        rtp = RiskTimePoint(days_ahead=7, risk_probability=0.3, risk_level="low")
        d = rtp.to_dict()
        assert d["days_ahead"] == 7
        assert d["risk_probability"] == 0.3


class TestRiskFactor:
    def test_create_and_to_dict(self):
        rf = RiskFactor(
            name="acwr",
            contribution=0.4,
            current_value=1.6,
            threshold_value=1.5,
            direction="increasing",
        )
        d = rf.to_dict()
        assert d["contribution"] == 0.4


class TestAcuteLoadRisk:
    def test_create_and_to_dict(self):
        alr = AcuteLoadRisk(
            atl_ctl_ratio=1.5, weekly_load_change_pct=20.0, risk_contribution=0.35
        )
        d = alr.to_dict()
        assert d["atl_ctl_ratio"] == 1.5


class TestChronicRisk:
    def test_create_and_to_dict(self):
        cr = ChronicRisk(
            tsb_consecutive_low_days=5,
            resting_hr_deviation_pct=8.0,
            risk_contribution=0.25,
        )
        d = cr.to_dict()
        assert d["tsb_consecutive_low_days"] == 5


class TestBodySignalRisk:
    def test_create_and_to_dict(self):
        bsr = BodySignalRisk(
            fatigue_score=65.0,
            recovery_status="yellow",
            active_alerts=["静息心率异常升高"],
            risk_contribution=0.2,
        )
        d = bsr.to_dict()
        assert d["fatigue_score"] == 65.0
        assert len(d["active_alerts"]) == 1


class TestInjuryRiskPrediction:
    def test_ml_enhanced(self):
        pred = InjuryRiskPrediction(
            risk_score=72.0,
            risk_level="high",
            risk_timeline=[
                RiskTimePoint(days_ahead=7, risk_probability=0.65, risk_level="high")
            ],
            acute_load_risk=AcuteLoadRisk(
                atl_ctl_ratio=1.8, weekly_load_change_pct=30.0, risk_contribution=0.4
            ),
            chronic_risk=ChronicRisk(
                tsb_consecutive_low_days=5,
                resting_hr_deviation_pct=12.0,
                risk_contribution=0.3,
            ),
            body_signal_risk=BodySignalRisk(
                fatigue_score=70.0,
                recovery_status="red",
                active_alerts=[],
                risk_contribution=0.2,
            ),
            top_risk_factors=[
                RiskFactor(
                    name="acwr",
                    contribution=0.4,
                    current_value=1.8,
                    threshold_value=1.5,
                    direction="increasing",
                )
            ],
            recommendations=["建议减量训练"],
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
        )
        assert pred.prediction_type == "ml_enhanced"
        assert pred.acute_load_risk is not None

    def test_parametric_optional_none(self):
        pred = InjuryRiskPrediction(
            risk_score=50.0,
            risk_level="medium",
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="parametric",
        )
        assert pred.acute_load_risk is None

    def test_basic_prediction_type(self):
        pred = InjuryRiskPrediction(
            risk_score=30.0,
            risk_level="low",
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="basic",
        )
        assert pred.prediction_type == "basic"

    def test_default_factory_lists(self):
        pred = InjuryRiskPrediction(
            risk_score=30.0,
            risk_level="low",
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="basic",
        )
        assert pred.top_risk_factors == []
        assert pred.recommendations == []

    def test_to_dict(self):
        pred = InjuryRiskPrediction(
            risk_score=72.0,
            risk_level="high",
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=["建议减量"],
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
        )
        d = pred.to_dict()
        assert d["risk_score"] == 72.0
        assert d["recommendations"] == ["建议减量"]


class TestPredictionRecord:
    def test_full_record(self):
        r = PredictionRecord(
            prediction_date="2026-05-08",
            prediction_type="vdot",
            predicted_value=46.8,
            predicted_unit="vdot",
            actual_value=None,
            deviation_pct=None,
            prediction_method="ml_enhanced",
            model_version="v1",
            confidence=0.85,
        )
        assert r.actual_value is None
        assert r.deviation_pct is None

    def test_to_dict(self):
        r = PredictionRecord(
            prediction_date="2026-05-08",
            prediction_type="vdot",
            predicted_value=46.8,
            predicted_unit="vdot",
            actual_value=None,
            deviation_pct=None,
            prediction_method="ml_enhanced",
            model_version="v1",
            confidence=0.85,
        )
        d = r.to_dict()
        assert d["prediction_date"] == "2026-05-08"
        assert d["actual_value"] is None


class TestTrainingResponse:
    def test_create_and_to_dict(self):
        tr = TrainingResponse(
            session_type="threshold",
            duration_min=60,
            intensity="high",
            predicted_vdot_impact=0.3,
            predicted_fatigue_impact=15.0,
            predicted_recovery_hours=48.0,
            predicted_injury_risk_delta=0.05,
            banister_fitness_delta=0.5,
            banister_fatigue_delta=8.0,
            prediction_type="parametric",
        )
        assert tr.prediction_type == "parametric"
        d = tr.to_dict()
        assert d["predicted_recovery_hours"] == 48.0


class TestInjuryReportResult:
    def test_create_and_to_dict(self):
        r = InjuryReportResult(
            injury_id="inj_20260508_001",
            injury_type="overuse",
            severity="moderate",
            date="2026-05-08",
            label_type="confirmed",
            created_at="2026-05-08T10:00:00",
            success=True,
        )
        d = r.to_dict()
        assert d["label_type"] == "confirmed"


class TestInjuryLabel:
    def test_create_and_to_dict(self):
        il = InjuryLabel(
            injury_id="inj_20260508_001",
            injury_type="overuse",
            severity="moderate",
            start_date="2026-05-01",
            end_date=None,
            label_type="confirmed",
            affected_sessions=["sess_001", "sess_002"],
            notes="膝盖疼痛",
        )
        d = il.to_dict()
        assert d["end_date"] is None
        assert len(d["affected_sessions"]) == 2


class TestSufficiencyDimension:
    def test_create_and_to_dict(self):
        sd = SufficiencyDimension(
            name="time_span_months",
            current_value=20.0,
            target_value=18.0,
            is_met=True,
            progress_pct=100.0,
        )
        d = sd.to_dict()
        assert d["is_met"] is True


class TestDataSufficiencyReport:
    def test_create_and_to_dict(self):
        r = DataSufficiencyReport(
            prediction_type="vdot",
            is_sufficient=True,
            overall_progress_pct=95.0,
            dimensions=[
                SufficiencyDimension(
                    name="time_span_months",
                    current_value=20.0,
                    target_value=18.0,
                    is_met=True,
                    progress_pct=100.0,
                )
            ],
            advice=["数据充足，可使用ML增强预测"],
        )
        d = r.to_dict()
        assert d["is_sufficient"] is True


class TestPredictionStatusReport:
    def test_create_and_to_dict(self):
        vdot_status = DataSufficiencyReport(
            prediction_type="vdot",
            is_sufficient=True,
            overall_progress_pct=95.0,
            dimensions=[],
            advice=[],
        )
        race_status = DataSufficiencyReport(
            prediction_type="race",
            is_sufficient=False,
            overall_progress_pct=40.0,
            dimensions=[],
            advice=[],
        )
        injury_status = DataSufficiencyReport(
            prediction_type="injury",
            is_sufficient=True,
            overall_progress_pct=90.0,
            dimensions=[],
            advice=[],
        )
        r = PredictionStatusReport(
            vdot_status=vdot_status,
            race_status=race_status,
            injury_status=injury_status,
            overall_ready_count=2,
            advice=["积累更多比赛数据"],
        )
        d = r.to_dict()
        assert d["overall_ready_count"] == 2


class TestModelMetadata:
    def test_create_and_to_dict(self):
        m = ModelMetadata(
            model_type="vdot_predictor",
            version="v1",
            trained_at="2026-05-08T10:00:00",
            training_samples=500,
            feature_count=12,
            validation_error=1.5,
            model_algorithm="gradient_boosting",
            sklearn_version="1.5.0",
            quantile_models=True,
            ensemble_weights=None,
        )
        d = m.to_dict()
        assert d["quantile_models"] is True
        assert d["ensemble_weights"] is None

    def test_with_ensemble_weights(self):
        m = ModelMetadata(
            model_type="injury_predictor",
            version="v1",
            trained_at="2026-05-08T10:00:00",
            training_samples=300,
            feature_count=8,
            validation_error=0.25,
            model_algorithm="lr_gbdt_ensemble",
            sklearn_version="1.5.0",
            quantile_models=False,
            ensemble_weights={"lr": 0.4, "gbdt": 0.6},
        )
        d = m.to_dict()
        assert d["ensemble_weights"] == {"lr": 0.4, "gbdt": 0.6}


class TestModelTrainingResult:
    def test_create_and_to_dict(self):
        r = ModelTrainingResult(
            model_type="vdot_predictor",
            version="v1",
            training_samples=500,
            validation_error=1.5,
            training_duration_seconds=45.0,
            success=True,
            message="训练完成",
        )
        d = r.to_dict()
        assert d["success"] is True


class TestModelManagementResult:
    def test_create_and_to_dict(self):
        r = ModelManagementResult(
            action="train",
            model_type="vdot_predictor",
            success=True,
            message="模型训练完成",
            details={},
        )
        d = r.to_dict()
        assert d["action"] == "train"


class TestModelStatus:
    def test_create_and_to_dict(self):
        s = ModelStatus(
            model_type="vdot_predictor",
            version="v1",
            trained_at="2026-05-08T10:00:00",
            training_samples=500,
            validation_error=1.5,
            is_available=True,
        )
        d = s.to_dict()
        assert d["is_available"] is True

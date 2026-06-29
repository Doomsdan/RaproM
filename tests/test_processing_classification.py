from __future__ import annotations

import numpy as np

import raprom.processing as processing
from raprom.processing import CheckType, PrepType


def test_prep_type_classifies_stratiform_transition_and_convective():
    dm_axes, nw_axes, matrix = PrepType(
        [[1.0, 1.1, 1.2, 1.3]],
        [[4.0, 4.6, 5.0, 5.2]],
    )

    def cell(dm: float, nw: float) -> float:
        return matrix[dm_axes.index(dm), nw_axes.index(nw)]

    assert cell(1.0, 4.0) == -5.0
    assert cell(1.1, 4.6) == 0.0
    assert cell(1.2, 5.0) == 5.0


def test_check_type_reclassifies_mixed_without_bright_band():
    hydrometeor_type = np.array([0.0, 0.0, 0.0, 0.0])
    nw = np.arange(4.0)
    dm = np.arange(10.0, 14.0)
    lwc = np.arange(20.0, 24.0)
    rr = np.arange(30.0, 34.0)
    ze = np.array([10.0, 11.5, 12.0, 13.5])
    skewness = np.array([-0.6, 0.1, 0.2, 0.2])
    velocity = np.array([1.0, 3.0, 1.5, 1.0])
    sigma = np.array([0.5, 0.5, 2.0, 0.5])
    kurtosis = np.zeros(4)
    snr = np.ones(4)

    checked, _, _, _, _ = CheckType(
        hydrometeor_type,
        np.nan,
        np.nan,
        100.0,
        nw.copy(),
        dm.copy(),
        lwc.copy(),
        rr.copy(),
        skewness,
        ze,
        kurtosis,
        snr,
        sigma,
        velocity,
    )

    assert checked.tolist() == [5.0, -15.0, 0.0, -10.0]


def test_check_type_converts_rain_above_bright_band_to_solid_and_clears_rain_fields():
    hydrometeor_type = np.array([10.0, 10.0, 10.0])
    nw = np.array([1.0, 2.0, 3.0])
    dm = np.array([4.0, 5.0, 6.0])
    lwc = np.array([7.0, 8.0, 9.0])
    rr = np.array([10.0, 11.0, 12.0])

    checked, checked_nw, checked_dm, checked_lwc, checked_rr = CheckType(
        hydrometeor_type,
        100.0,
        150.0,
        100.0,
        nw,
        dm,
        lwc,
        rr,
        np.array([0.0, 0.0, -0.6]),
        np.array([1.0, 2.0, 3.0]),
        np.zeros(3),
        np.ones(3),
        np.ones(3),
        np.array([1.0, 1.0, 1.0]),
    )

    assert checked.tolist() == [10.0, 10.0, -10.0]
    assert np.isnan(checked_nw[2])
    assert np.isnan(checked_dm[2])
    assert np.isnan(checked_lwc[2])
    assert np.isnan(checked_rr[2])


def test_mie_efficiencies_supports_new_miepython_api(monkeypatch):
    class NewMieApi:
        @staticmethod
        def efficiencies_mx(_m, _x):
            return 1.0, 2.0, 3.0, 4.0

    monkeypatch.setattr(processing, "mp", NewMieApi())

    assert processing.mie_efficiencies(1.0 + 0.1j, 2.0) == (1.0, 2.0, 3.0, 4.0)


def test_processing_velocity_vectors_are_module_globals():
    assert len(processing.speed) == 64
    assert len(processing.speed2) == 64
    assert processing.speed[0] == 0.0

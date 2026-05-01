from app.utils.travel_style import normalize_travel_style


def test_normalize_travel_style_family_trip() -> None:
    assert normalize_travel_style("family trip") == "Family"


def test_normalize_travel_style_young_kids_activities() -> None:
    assert normalize_travel_style("young kids activities") == "Family"


def test_normalize_travel_style_luxury_resorts() -> None:
    assert normalize_travel_style("luxury resorts") == "Luxury"

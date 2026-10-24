from identity_aids import (
    address_features,
    category_features,
    name_features,
    normalize_phone,
    pair_review_aids,
)


def test_lepimp_name_normalization():
    f = name_features("Lepimp", "lepimp")
    assert f["relation"] == "EXACT_NORMALIZED"
    assert f["strict_sequence_similarity"] == 1.0


def test_articles_are_soft_not_strict():
    f = name_features("La Esquina", "Esquina")
    assert f["strict_sequence_similarity"] < 1.0
    assert f["core_sequence_similarity"] == 1.0


def test_bogota_fixed_line_country_code():
    assert normalize_phone("+57 601 621 2614") == "6016212614"


def test_corner_address_pattern():
    f = address_features("Cl 82 # 9 - 09, Bogotá", "Carrera 9 81-18")
    assert f["street_cross_near"] is True
    assert f["relation"] == "ADJACENT_CORNER_PATTERN"


def test_bar_category_compatibility():
    a = {"basic_category": "bar", "hierarchy": ["food_and_drink", "bar"]}
    b = {"fsq_category_labels": ["Dining and Drinking > Bar > Cocktail Bar"]}
    f = category_features(a, b)
    assert f["relation"] == "COMPATIBLE_FAMILY"
    assert "food_and_drink" in f["shared_families"]


def test_pair_aids_exact_phone_and_name():
    f = pair_review_aids(
        name_a="Bagatelle",
        name_b="Bagatelle",
        phone_a="+576016212614",
        phone_b="+57 601 6212614",
        address_a="Cl 82 # 9 - 09",
        address_b="Carrera 9 81-18",
        category_a="bakery restaurant",
        category_b="restaurant",
        lat_a=4.664706753248518,
        lon_a=-74.05128218036977,
        lat_b=4.6640348,
        lon_b=-74.0514048,
    )
    assert f["phone"]["exact"] is True
    assert f["name"]["relation"] == "EXACT_NORMALIZED"
    assert 70 <= f["coordinate_distance_m"] <= 82

import pytest
from load_contract import accepted, validate_profiles, validate_target


def test_zero_and_incomplete_checkout_cannot_pass():
    counts = dict(completed_checkouts=2, peak_users=10, failures=0)
    audit = dict(orders=2, paid_orders=2, payments=2, provider_effects=2, duplicate_intents=0)
    assert accepted(counts, audit, 10, 0)
    assert not accepted({**counts, "completed_checkouts": 0}, audit, 10, 0)
    assert not accepted(counts, {**audit, "paid_orders": 1}, 10, 0)
    assert not accepted(counts, {**audit, "provider_effects": 3}, 10, 0)
    assert not accepted(counts, {**audit, "duplicate_intents": 1}, 10, 0)
    assert not accepted(counts, audit, 100, 0)
    assert not accepted(counts, audit, 10, 124)
    assert not accepted({**counts, "failures": 1}, audit, 10, 0)


@pytest.mark.parametrize("field", ["base_url", "provider_direct_url", "database_url"])
def test_load_refuses_remote_service(tmp_path, field):
    (tmp_path / ".commerce-test-run").touch()
    config = dict(
        run_dir=str(tmp_path),
        base_url="http://127.0.0.1:1",
        provider_direct_url="http://127.0.0.1:2",
        database_url="postgresql://127.0.0.1/db",
    )
    validate_target(config, tmp_path / "config.json")
    config[field] = "https://production.example"
    with pytest.raises(ValueError, match="loopback"):
        validate_target(config, tmp_path / "config.json")


@pytest.mark.parametrize(
    "profiles",
    [
        [],
        [["spike", 1000, 1, 10]],
        [["spike", 1001, 100, 30]],
        [["smoke", True, 1, 10]],
        [["a", 1, 1, 10], ["a", 1, 1, 10]],
    ],
)
def test_empty_unachievable_or_unsafe_profiles_rejected(profiles):
    with pytest.raises(ValueError):
        validate_profiles(profiles)

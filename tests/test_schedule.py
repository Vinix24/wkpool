"""Integrity of the static 2026 tournament data."""
import itertools

from wkpool import schedule


def test_groups_are_complete():
    assert len(schedule.GROUPS) == 12
    teams = schedule.all_teams()
    assert len(teams) == 48
    assert len(set(teams)) == 48
    for letter, group in schedule.GROUPS.items():
        assert len(group) == 4, f"group {letter}"


def test_72_fixtures_three_per_team():
    assert len(schedule.GROUP_FIXTURES) == 72
    appearances: dict[str, int] = {}
    for _, home, away in schedule.GROUP_FIXTURES:
        appearances[home] = appearances.get(home, 0) + 1
        appearances[away] = appearances.get(away, 0) + 1
        assert schedule.group_of(home) == schedule.group_of(away), \
            f"{home} vs {away} crosses groups"
    assert all(n == 3 for n in appearances.values())
    assert len(appearances) == 48


def test_fixture_dates_in_group_stage_window():
    for date, _, _ in schedule.GROUP_FIXTURES:
        assert "2026-06-11" <= date <= "2026-06-28"


def test_round_of_32_structure():
    assert len(schedule.ROUND_OF_32) == 16
    winners = [m["home"][1] for m in schedule.ROUND_OF_32 if m["home"][0] == "1"]
    winners += [m["away"][1] for m in schedule.ROUND_OF_32 if m["away"][0] == "1"]
    assert sorted(winners) == sorted(schedule.GROUP_LETTERS), \
        "every group winner appears exactly once"
    runners = [m["home"][1] for m in schedule.ROUND_OF_32 if m["home"][0] == "2"]
    runners += [m["away"][1] for m in schedule.ROUND_OF_32 if m["away"][0] == "2"]
    assert sorted(runners) == sorted(schedule.GROUP_LETTERS), \
        "every runner-up appears exactly once"
    thirds = [m for m in schedule.ROUND_OF_32 if m["away"][0] == "3"]
    assert len(thirds) == 8


def test_knockout_tree_is_closed():
    r32_numbers = {m["match"] for m in schedule.ROUND_OF_32}
    assert r32_numbers == set(range(73, 89))
    r16_feeds = {n for pair in schedule.ROUND_OF_16.values() for n in pair}
    assert r16_feeds == r32_numbers, "R16 consumes each R32 match exactly once"
    qf_feeds = {n for pair in schedule.QUARTER_FINALS.values() for n in pair}
    assert qf_feeds == set(schedule.ROUND_OF_16)
    sf_feeds = {n for pair in schedule.SEMI_FINALS.values() for n in pair}
    assert sf_feeds == set(schedule.QUARTER_FINALS)
    assert set(schedule.FINAL) == set(schedule.SEMI_FINALS)


def test_third_allocation_feasible_for_every_combination():
    """FIFA designed the slots so any 8-of-12 qualified thirds can be seated."""
    slots = [m["away"][1] for m in schedule.ROUND_OF_32 if m["away"][0] == "3"]
    for combo in itertools.combinations(schedule.GROUP_LETTERS, 8):
        assignment = schedule.allocate_thirds(list(combo))
        assert assignment is not None, f"no valid seating for {combo}"
        assert sorted(assignment.values()) == sorted(combo)
        assert sorted(assignment.keys()) == sorted(slots)
        for slot, group in assignment.items():
            assert group in slot

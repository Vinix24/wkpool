"""Static FIFA World Cup 2026 tournament data.

Facts (group draw of 5 December 2025, the 72 published group fixtures and
the official knockout bracket, matches 73-104) are taken from the official
FIFA match schedule. Team names follow the conventions of the
martj42/international_results dataset so they join cleanly.
"""
from __future__ import annotations

GROUP_LETTERS = "ABCDEFGHIJKL"

# Group draw of 5 December 2025, Washington D.C.
GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "South Africa", "Czech Republic"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curaçao"],
    "F": ["Netherlands", "Japan", "Tunisia", "Sweden"],
    "G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "DR Congo"],
    "L": ["England", "Croatia", "Panama", "Ghana"],
}

# All 72 group fixtures with official dates: (date, home, away).
# "home" is the first-listed team; all matches are on neutral ground for
# rating purposes except the three host nations.
GROUP_FIXTURES: list[tuple[str, str, str]] = [
    ("2026-06-11", "Mexico", "South Africa"),
    ("2026-06-12", "South Korea", "Czech Republic"),
    ("2026-06-12", "Canada", "Bosnia and Herzegovina"),
    ("2026-06-13", "United States", "Paraguay"),
    ("2026-06-13", "Qatar", "Switzerland"),
    ("2026-06-13", "Brazil", "Morocco"),
    ("2026-06-14", "Haiti", "Scotland"),
    ("2026-06-14", "Australia", "Turkey"),
    ("2026-06-14", "Germany", "Curaçao"),
    ("2026-06-14", "Netherlands", "Japan"),
    ("2026-06-15", "Ivory Coast", "Ecuador"),
    ("2026-06-15", "Sweden", "Tunisia"),
    ("2026-06-15", "Spain", "Cape Verde"),
    ("2026-06-15", "Belgium", "Egypt"),
    ("2026-06-15", "Saudi Arabia", "Uruguay"),
    ("2026-06-16", "Iran", "New Zealand"),
    ("2026-06-16", "France", "Senegal"),
    ("2026-06-16", "Iraq", "Norway"),
    ("2026-06-17", "Argentina", "Algeria"),
    ("2026-06-17", "Austria", "Jordan"),
    ("2026-06-17", "Portugal", "DR Congo"),
    ("2026-06-17", "England", "Croatia"),
    ("2026-06-18", "Ghana", "Panama"),
    ("2026-06-18", "Uzbekistan", "Colombia"),
    ("2026-06-18", "Czech Republic", "South Africa"),
    ("2026-06-18", "Switzerland", "Bosnia and Herzegovina"),
    ("2026-06-18", "Canada", "Qatar"),
    ("2026-06-19", "Mexico", "South Korea"),
    ("2026-06-19", "United States", "Australia"),
    ("2026-06-19", "Scotland", "Morocco"),
    ("2026-06-20", "Brazil", "Haiti"),
    ("2026-06-20", "Turkey", "Paraguay"),
    ("2026-06-20", "Netherlands", "Sweden"),
    ("2026-06-20", "Germany", "Ivory Coast"),
    ("2026-06-21", "Ecuador", "Curaçao"),
    ("2026-06-21", "Tunisia", "Japan"),
    ("2026-06-21", "Spain", "Saudi Arabia"),
    ("2026-06-21", "Belgium", "Iran"),
    ("2026-06-21", "Uruguay", "Cape Verde"),
    ("2026-06-22", "New Zealand", "Egypt"),
    ("2026-06-22", "Argentina", "Austria"),
    ("2026-06-22", "France", "Iraq"),
    ("2026-06-23", "Norway", "Senegal"),
    ("2026-06-23", "Jordan", "Algeria"),
    ("2026-06-23", "Portugal", "Uzbekistan"),
    ("2026-06-23", "England", "Ghana"),
    ("2026-06-24", "Panama", "Croatia"),
    ("2026-06-24", "Colombia", "DR Congo"),
    ("2026-06-24", "Switzerland", "Canada"),
    ("2026-06-24", "Bosnia and Herzegovina", "Qatar"),
    ("2026-06-24", "Morocco", "Haiti"),
    ("2026-06-24", "Scotland", "Brazil"),
    ("2026-06-25", "South Africa", "South Korea"),
    ("2026-06-25", "Czech Republic", "Mexico"),
    ("2026-06-25", "Curaçao", "Ivory Coast"),
    ("2026-06-25", "Ecuador", "Germany"),
    ("2026-06-26", "Tunisia", "Netherlands"),
    ("2026-06-26", "Japan", "Sweden"),
    ("2026-06-26", "Turkey", "United States"),
    ("2026-06-26", "Paraguay", "Australia"),
    ("2026-06-26", "Norway", "France"),
    ("2026-06-26", "Senegal", "Iraq"),
    ("2026-06-27", "Cape Verde", "Saudi Arabia"),
    ("2026-06-27", "Uruguay", "Spain"),
    ("2026-06-27", "New Zealand", "Belgium"),
    ("2026-06-27", "Egypt", "Iran"),
    ("2026-06-27", "Panama", "England"),
    ("2026-06-27", "Croatia", "Ghana"),
    ("2026-06-28", "Colombia", "Portugal"),
    ("2026-06-28", "DR Congo", "Uzbekistan"),
    ("2026-06-28", "Algeria", "Austria"),
    ("2026-06-28", "Jordan", "Argentina"),
]

HOSTS = {"Mexico", "United States", "Canada"}

# Official round of 32 (matches 73-88). Slot encoding:
#   ("1", "E")      -> winner of group E
#   ("2", "A")      -> runner-up of group A
#   ("3", "ABCDF")  -> a qualified third-placed team from one of these groups
ROUND_OF_32: list[dict] = [
    {"match": 73, "date": "2026-06-28", "home": ("2", "A"), "away": ("2", "B")},
    {"match": 74, "date": "2026-06-29", "home": ("1", "E"), "away": ("3", "ABCDF")},
    {"match": 75, "date": "2026-06-29", "home": ("1", "F"), "away": ("2", "C")},
    {"match": 76, "date": "2026-06-29", "home": ("1", "C"), "away": ("2", "F")},
    {"match": 77, "date": "2026-06-30", "home": ("1", "I"), "away": ("3", "CDFGH")},
    {"match": 78, "date": "2026-06-30", "home": ("2", "E"), "away": ("2", "I")},
    {"match": 79, "date": "2026-06-30", "home": ("1", "A"), "away": ("3", "CEFHI")},
    {"match": 80, "date": "2026-07-01", "home": ("1", "L"), "away": ("3", "EHIJK")},
    {"match": 81, "date": "2026-07-01", "home": ("1", "D"), "away": ("3", "BEFIJ")},
    {"match": 82, "date": "2026-07-01", "home": ("1", "G"), "away": ("3", "AEHIJ")},
    {"match": 83, "date": "2026-07-02", "home": ("2", "K"), "away": ("2", "L")},
    {"match": 84, "date": "2026-07-02", "home": ("1", "H"), "away": ("2", "J")},
    {"match": 85, "date": "2026-07-02", "home": ("1", "B"), "away": ("3", "EFGIJ")},
    {"match": 86, "date": "2026-07-03", "home": ("1", "J"), "away": ("2", "H")},
    {"match": 87, "date": "2026-07-03", "home": ("1", "K"), "away": ("3", "DEIJL")},
    {"match": 88, "date": "2026-07-03", "home": ("2", "D"), "away": ("2", "G")},
]

# Knockout tree: match number -> (home = winner of, away = winner of)
ROUND_OF_16: dict[int, tuple[int, int]] = {
    89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
    93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
}
QUARTER_FINALS: dict[int, tuple[int, int]] = {
    97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96),
}
SEMI_FINALS: dict[int, tuple[int, int]] = {101: (97, 98), 102: (99, 100)}
FINAL: tuple[int, int] = (101, 102)

ROUND_NAMES = ["R32", "R16", "QF", "SF", "F"]


def all_teams() -> list[str]:
    return [t for g in GROUPS.values() for t in g]


def group_of(team: str) -> str:
    for letter, teams in GROUPS.items():
        if team in teams:
            return letter
    raise KeyError(f"{team} is not in any 2026 group")


def fixtures_of_group(letter: str) -> list[tuple[str, str, str]]:
    teams = set(GROUPS[letter])
    return [f for f in GROUP_FIXTURES if f[1] in teams]


def allocate_thirds(qualified: list[str], slots: list[str] | None = None) -> dict[str, str] | None:
    """Assign 8 qualified third-place groups to the 8 third-place bracket slots.

    `qualified` is a list of 8 group letters, ordered best third first.
    Returns {slot_allowed_groups: assigned_group_letter} or None if no valid
    assignment exists (FIFA designed the slots so one always does).

    Deterministic: slots with the fewest options are filled first, and within
    a slot the better-ranked third is preferred. This mirrors the constraint
    structure of FIFA's allocation procedure; the exact FIFA priority order
    is not public, so ties between valid assignments may differ from FIFA's.
    """
    if slots is None:
        slots = [m["away"][1] for m in ROUND_OF_32 if m["away"][0] == "3"]
    order = sorted(slots, key=lambda s: sum(1 for g in qualified if g in s))

    assignment: dict[str, str] = {}
    used: set[str] = set()

    def backtrack(i: int) -> bool:
        if i == len(order):
            return True
        slot = order[i]
        for g in qualified:  # qualified is ranked best-first
            if g in slot and g not in used:
                assignment[slot] = g
                used.add(g)
                if backtrack(i + 1):
                    return True
                used.remove(g)
                del assignment[slot]
        return False

    return assignment if backtrack(0) else None

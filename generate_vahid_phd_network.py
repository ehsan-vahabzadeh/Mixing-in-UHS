"""
Generate a publication/collaboration network for Vahid.

Before running:
    1. Change INPUT_FILE below, or pass --input on the command line.
    2. Install dependencies if needed:
       pip install pandas networkx matplotlib adjustText openpyxl

Outputs:
    vahid_phd_network_viridis.png
    vahid_phd_network_viridis.pdf
    vahid_phd_network_magenta.png
    vahid_phd_network_magenta.pdf
    vahid_phd_network_inferno.png
    vahid_phd_network_inferno.pdf
    phd_coauthorship_summary.csv
"""

from __future__ import annotations

import argparse
import math
import re
import textwrap
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D

try:
    from adjustText import adjust_text
except ImportError:  # The plot still works without adjustText.
    adjust_text = None


# ---------------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------------

INPUT_FILE = Path("publications.xlsx")  # Change this to your CSV/XLSX path.
SHEET_NAME = 0  # Excel sheet name or index. Ignored for CSV files.
OUTPUT_DIR = Path(".")

INCLUDE_PROJECT_COLLABORATORS = True
SHOW_SUPERVISION_FALLBACK_FOR_ZERO_PAPER_STUDENTS = True

# If True, a student-student co-authorship edge is counted only for papers
# where Vahid is also identified in the author list.
REQUIRE_VAHID_ON_PAPER_FOR_COAUTHORSHIP = False

# Student-student co-authorship edges connect only the matched first-author
# student to other matched student co-authors on that paper. Later co-authors
# are not connected to each other just because they appear on the same paper.

# Vahid-student paper lines are drawn only for papers where the listed PhD
# student is matched as the first author and Vahid is also on the paper.
REQUIRE_STUDENT_FIRST_AUTHOR_FOR_VAHID_STUDENT_LINES = True

# "spring" keeps Vahid fixed at the center. "kamada_kawai" is also available.
LAYOUT = "spring"
LAYOUT_SEED = 7

OUTPUT_PREFIX = "vahid_phd_network"
OUTPUT_SUMMARY_CSV = "phd_coauthorship_summary.csv"


# ---------------------------------------------------------------------------
# People and aliases
# ---------------------------------------------------------------------------

VAHID_NODE = "Vahid Niasar"

VAHID_ALIASES = [
    "V Niasar",
    "VJ Niasar",
    "V J Niasar",
    "Vahid Niasar",
    "Vahid J Niasar",
    "V Joekar-Niasar",
    "V Joekar Niasar",
    "Vahid Joekar-Niasar",
    "Vahid Joekar Niasar",
]


@dataclass(frozen=True)
class Student:
    name: str
    status: str  # "current" or "graduate"
    period: str
    aliases: tuple[str, ...]


STUDENTS = [
    Student(
        "Grace Esu-Ejienot Aguah",
        "current",
        "PhD since 2022",
        (
            "GEE Aguah",
            "G E E Aguah",
            "GEE Aquah",
            "G E E Aquah",
            "Grace Aguah",
            "Grace Esu-Ejienot Aguah",
        ),
    ),
    Student(
        "Ehsan Vahabzadeh",
        "current",
        "PhD since 2022",
        ("E Vahabzadeh", "Ehsan Vahabzadeh"),
    ),
    Student(
        "Tongke Zhou",
        "current",
        "PhD since 2022",
        ("T Zhou", "Tongke Zhou"),
    ),
    Student(
        "Sina Omrani",
        "current",
        "PhD since 2022",
        ("S Omrani", "Sina Omrani"),
    ),
    Student(
        "Saleh Mohammadrezaei",
        "current",
        "PhD since 2023",
        ("S Mohammadrezaei", "Saleh Mohammadrezaei"),
    ),
    Student(
        "Mahtab Shahrzadi",
        "current",
        "PhD since 2023",
        ("M Shahrzadi", "Mahtab Shahrzadi"),
    ),
    Student(
        "Yiqi Sun",
        "current",
        "PhD since 2023",
        ("Y Sun", "Yiqi Sun"),
    ),
    Student(
        "Arash Pourakaberian",
        "current",
        "PhD since 2023",
        ("A Pourakaberian", "Arash Pourakaberian"),
    ),
    Student(
        "Qiuheng Xie",
        "current",
        "PhD since 2024",
        ("Q Xie", "Qiuheng Xie"),
    ),
    Student(
        "Wenxing Dai",
        "current",
        "PhD since 2025",
        ("W Dai", "Wenxing Dai"),
    ),
    Student(
        "Mikhail Serebrenny",
        "current",
        "PhD since 2025",
        ("M Serebrenny", "Mikhail Serebrenny"),
    ),
    Student(
        "Dr Rimsha Aziz",
        "graduate",
        "PhD 2015-2018",
        ("R Aziz", "Rimsha Aziz", "Dr Rimsha Aziz"),
    ),
    Student(
        "Dr Omar E. Godinez Brizuela",
        "graduate",
        "MPhil/PhD 2015-2020",
        (
            "OE Godinez-Brizuela",
            "O E Godinez Brizuela",
            "Omar E Godinez Brizuela",
            "OG Brizuela",
            "O G Brizuela",
            "Omar Godinez-Brizuela",
            "Omar Godinez Brizuela",
            "Dr Omar E Godinez Brizuela",
        ),
    ),
    Student(
        "Dr Sharul Nizam Hasan",
        "graduate",
        "PhD 2016-2020",
        (
            "S Hasan",
            "Sharul Hasan",
            "Sharul Nizam Hasan",
            "Dr Sharul Nizam Hasan",
        ),
    ),
    Student(
        "Dr Daniel Niblett",
        "graduate",
        "PhD 2017-2021",
        ("D Niblett", "Daniel Niblett", "Dr Daniel Niblett"),
    ),
    Student(
        "Dr Hamidreza Erfani",
        "graduate",
        "PhD 2017-2020",
        ("H Erfani", "Hamidreza Erfani", "Dr Hamidreza Erfani"),
    ),
    Student(
        "Dr Senyou An",
        "graduate",
        "PhD 2018-2021",
        ("S An", "Senyou An", "Dr Senyou An"),
    ),
    Student(
        "Dr Takshak Shende",
        "graduate",
        "PhD 2019-2022",
        ("T Shende", "Takshak Shende", "Dr Takshak Shende"),
    ),
    Student(
        "Dr Javad Shokri",
        "graduate",
        "PhD 2019-2023",
        ("J Shokri", "Javad Shokri", "Dr Javad Shokri"),
    ),
    Student(
        "Dr Farzaneh Nazari",
        "graduate",
        "PhD 2021-2025",
        ("F Nazari", "Farzaneh Nazari", "Dr Farzaneh Nazari"),
    ),
    Student(
        "Dr Amna Al-Qenae",
        "graduate",
        "PhD 2021-2025",
        ("A Al-Qenae", "A Al Qenae", "Amna Al-Qenae", "Amna Al Qenae"),
    ),
]


GRADUATE_CURRENT_ROLES = {
    "Dr Farzaneh Nazari": "Scientist",
    "Dr Javad Shokri": "Engineer",
    "Dr Amna Al-Qenae": "Engineer",
    "Dr Rimsha Aziz": "Engineer",
    "Dr Omar E. Godinez Brizuela": "Scientist",
    "Dr Daniel Niblett": "Fellow",
    "Dr Sharul Nizam Hasan": "Professor",
    "Dr Senyou An": "Professor",
    "Dr Hamidreza Erfani": "Scientist",
    "Dr Takshak Shende": "Scientist",
}

CURRENT_STUDENT_COLLABORATORS = {
    "Sina Omrani": "ASTAR",
    "Saleh Mohammadrezaei": "SHELL",
    "Ehsan Vahabzadeh": "BP",
    "Mahtab Shahrzadi": "Johnson Matthey",
    "Arash Pourakaberian": "Halliburton",
    "Wenxing Dai": "SHELL",
    "Tongke Zhou": "SIMM Lab",
}

DISPLAY_LABEL_OVERRIDES = {
    "Dr Hamidreza Erfani": "Hamid",
}


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

COLOR_THEMES = {
    "viridis": {
        "node": {
            "vahid": "#FDE725",
            "current": "#35B779",
            "graduate": "#31688E",
            "role": "#CDE9C7",
            "collaborator": "#B8DE29",
        },
        "edge": {
            "vahid_paper": "#440154",
            "supervision_fallback": "#9E9E9E",
            "coauthorship": "#21918C",
            "role": "#7AD151",
            "collaborator": "#3B528B",
        },
        "font": {
            "vahid": "#111111",
            "current": "#111111",
            "graduate": "#111111",
            "role": "#111111",
            "collaborator": "#111111",
        },
        "node_edge": "#111111",
    },
    "magenta": {
        "node": {
            "vahid": "#8E005F",
            "current": "#D81B60",
            "graduate": "#7B3294",
            "role": "#F1D4E5",
            "collaborator": "#F8BBD0",
        },
        "edge": {
            "vahid_paper": "#5C004A",
            "supervision_fallback": "#9E9E9E",
            "coauthorship": "#C51B7D",
            "role": "#A6A6A6",
            "collaborator": "#E7298A",
        },
        "font": {
            "vahid": "white",
            "current": "white",
            "graduate": "white",
            "role": "#111111",
            "collaborator": "#111111",
        },
        "node_edge": "white",
    },
    "inferno": {
        "node": {
            "vahid": "#FCFFA4",
            "current": "#F98E09",
            "graduate": "#BC3754",
            "role": "#F1E6D6",
            "collaborator": "#F6D746",
        },
        "edge": {
            "vahid_paper": "#000004",
            "supervision_fallback": "#9E9E9E",
            "coauthorship": "#D44842",
            "role": "#7A7A7A",
            "collaborator": "#932667",
        },
        "font": {
            "vahid": "#111111",
            "current": "#111111",
            "graduate": "white",
            "role": "#111111",
            "collaborator": "#111111",
        },
        "node_edge": "#111111",
    },
}

COLOR_THEME_ORDER = ("viridis", "magenta", "inferno")

NODE_SIZES = {
    "vahid": 12600,
    "student": 6900,
    "role": 4100,
    "collaborator": 4100,
}

LEFT_CURRENT_TIGHTEN_FACTOR = 0.88
LEFT_CURRENT_SHIFT_X = 0.28
GRADUATE_SPREAD_FACTOR = 1.42


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

TITLE_TOKENS = {"dr", "prof", "professor", "mr", "mrs", "ms", "miss"}


def normalize_name(value: object) -> str:
    """Normalize author names for alias matching."""
    if value is None or pd.isna(value):
        return ""

    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()

    # Treat hyphenated surnames and initials consistently.
    text = re.sub(r"[\u2010-\u2015\-]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    parts = [part for part in text.split() if part not in TITLE_TOKENS]
    return " ".join(parts)


def expand_initial_variants(normalized_name: str) -> set[str]:
    """Add variants such as 'vj niasar' <-> 'v j niasar'."""
    normalized_name = " ".join(normalized_name.split())
    if not normalized_name:
        return set()

    variants = {normalized_name}
    parts = normalized_name.split()
    if len(parts) < 2:
        return variants

    first = parts[0]
    if 1 < len(first) <= 4 and first.isalpha():
        variants.add(" ".join(list(first) + parts[1:]))

    leading_initials = []
    for part in parts:
        if len(part) == 1 and part.isalpha():
            leading_initials.append(part)
        else:
            break

    if len(leading_initials) >= 2:
        variants.add("".join(leading_initials) + " " + " ".join(parts[len(leading_initials) :]))

    return variants


def generated_aliases_from_display_name(display_name: str) -> set[str]:
    """Generate simple first-initial/surname aliases from a full name."""
    normalized = normalize_name(display_name)
    parts = normalized.split()
    if len(parts) < 2:
        return {normalized}

    first = parts[0]
    surname = parts[-1]
    middle_initials = "".join(part[0] for part in parts[1:-1])
    all_initials = first[0] + middle_initials

    aliases = {
        normalized,
        f"{first} {surname}",
        f"{first[0]} {surname}",
        f"{all_initials} {surname}",
        " ".join(list(all_initials) + [surname]),
    }
    return {alias for alias in aliases if alias.strip()}


def build_alias_lookup() -> dict[str, set[str]]:
    """Map every normalized alias to one or more canonical people."""
    lookup: dict[str, set[str]] = defaultdict(set)

    for alias in VAHID_ALIASES:
        for variant in expand_initial_variants(normalize_name(alias)):
            lookup[variant].add(VAHID_NODE)

    for student in STUDENTS:
        aliases = set(student.aliases)
        aliases.add(student.name)
        aliases.update(generated_aliases_from_display_name(student.name))

        for alias in aliases:
            for variant in expand_initial_variants(normalize_name(alias)):
                lookup[variant].add(student.name)

    collisions = {alias: people for alias, people in lookup.items() if len(people) > 1}
    if collisions:
        print("Warning: some aliases match more than one person:")
        for alias, people in sorted(collisions.items()):
            print(f"  {alias!r}: {', '.join(sorted(people))}")

    return lookup


def author_name_variants(author_text: str) -> set[str]:
    """Return possible normalized forms for one author string."""
    variants = set()

    normalized = normalize_name(author_text)
    variants.update(expand_initial_variants(normalized))

    # Handle surname-first forms: "Niasar, VJ" -> "VJ Niasar".
    raw = str(author_text)
    if "," in raw:
        before, after = raw.split(",", 1)
        swapped = f"{after} {before}"
        variants.update(expand_initial_variants(normalize_name(swapped)))

    # Handle compact surname-first forms without commas: "Niasar VJ".
    parts = normalized.split()
    if len(parts) >= 2 and 1 <= len(parts[-1]) <= 4:
        swapped = " ".join([parts[-1]] + parts[:-1])
        variants.update(expand_initial_variants(swapped))

    return variants


def split_authors(author_cell: object) -> list[str]:
    """Split the Authors as shown cell. The expected separator is semicolon."""
    if author_cell is None or pd.isna(author_cell):
        return []

    text = str(author_cell)
    text = text.replace("\r", ";").replace("\n", ";")
    parts = re.split(r"\s*;\s*", text)
    return [part.strip() for part in parts if part.strip()]


def identify_people(author_cell: object, alias_lookup: dict[str, set[str]]) -> set[str]:
    """Identify Vahid and listed PhD students in one author cell."""
    matched: set[str] = set()

    for author in split_authors(author_cell):
        for variant in author_name_variants(author):
            matched.update(alias_lookup.get(variant, set()))

    return matched


# ---------------------------------------------------------------------------
# Data loading and co-authorship extraction
# ---------------------------------------------------------------------------

def normalized_column_key(column_name: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(column_name).strip().lower())


def find_column(df: pd.DataFrame, possible_names: list[str]) -> str:
    lookup = {normalized_column_key(column): column for column in df.columns}
    for possible_name in possible_names:
        key = normalized_column_key(possible_name)
        if key in lookup:
            return lookup[key]

    raise ValueError(
        "Could not find any of these columns: "
        + ", ".join(possible_names)
        + f". Available columns are: {', '.join(map(str, df.columns))}"
    )


def read_publications(input_file: Path, sheet_name: object) -> pd.DataFrame:
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    suffix = input_file.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(input_file, sheet_name=sheet_name)

    if suffix == ".csv":
        try:
            return pd.read_csv(input_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(input_file, encoding="latin1")

    raise ValueError("Input file must be .csv, .xlsx, .xls, or .xlsm")


def clean_title(value: object, fallback: str) -> str:
    if value is None or pd.isna(value):
        return fallback

    title = " ".join(str(value).split())
    return title if title else fallback


def extract_coauthorships(
    df: pd.DataFrame,
    alias_lookup: dict[str, set[str]],
    require_vahid: bool = False,
    require_student_first_author_for_edges: bool = True,
) -> tuple[
    dict[tuple[str, str], dict[str, object]],
    dict[str, list[str]],
    dict[str, object],
]:
    """Return student co-authorships, Vahid-student paper lists, and diagnostics."""
    title_column = find_column(df, ["Title", "Publication title", "Paper title"])
    authors_column = find_column(df, ["Authors as shown", "Authors", "Author(s)", "Author list"])

    student_names = {student.name for student in STUDENTS}
    student_order = {student.name: index for index, student in enumerate(STUDENTS)}
    coauthorships: dict[tuple[str, str], dict[str, object]] = {}
    vahid_student_papers: dict[str, list[str]] = {
        student.name: [] for student in STUDENTS
    }

    diagnostics = {
        "rows": len(df),
        "papers_with_any_student": 0,
        "papers_with_student_pairs": 0,
        "papers_with_vahid": 0,
        "vahid_student_paper_edges": 0,
    }

    for row_number, row in df.iterrows():
        title = clean_title(row.get(title_column), fallback=f"Untitled row {row_number + 1}")
        author_cell = row.get(authors_column)
        authors = split_authors(author_cell)
        people = identify_people(author_cell, alias_lookup)
        first_author_people = identify_people(authors[0], alias_lookup) if authors else set()

        if VAHID_NODE in people:
            diagnostics["papers_with_vahid"] += 1

        if require_vahid and VAHID_NODE not in people:
            continue

        paper_students = sorted(
            people.intersection(student_names),
            key=lambda name: student_order[name],
        )

        if paper_students:
            diagnostics["papers_with_any_student"] += 1

        if VAHID_NODE in people:
            if require_student_first_author_for_edges:
                vahid_edge_students = [
                    student for student in paper_students if student in first_author_people
                ]
            else:
                vahid_edge_students = paper_students

            for student in vahid_edge_students:
                vahid_student_papers[student].append(title)
                diagnostics["vahid_student_paper_edges"] += 1

        first_author_students = sorted(
            (student for student in paper_students if student in first_author_people),
            key=lambda name: student_order[name],
        )
        first_author_student = first_author_students[0] if first_author_students else None

        if first_author_student and len(paper_students) >= 2:
            diagnostics["papers_with_student_pairs"] += 1

        for coauthor_student in paper_students:
            if not first_author_student or coauthor_student == first_author_student:
                continue

            key = tuple(
                sorted(
                    (first_author_student, coauthor_student),
                    key=lambda name: student_order[name],
                )
            )
            if key not in coauthorships:
                coauthorships[key] = {"count": 0, "titles": []}

            coauthorships[key]["count"] = int(coauthorships[key]["count"]) + 1
            coauthorships[key]["titles"].append(title)

    return coauthorships, vahid_student_papers, diagnostics


def write_coauthorship_summary(
    coauthorships: dict[tuple[str, str], dict[str, object]],
    output_csv: Path,
) -> None:
    rows = []
    for (student_1, student_2), data in sorted(
        coauthorships.items(),
        key=lambda item: (-int(item[1]["count"]), item[0][0], item[0][1]),
    ):
        titles = list(dict.fromkeys(data["titles"]))
        rows.append(
            {
                "Student 1": student_1,
                "Student 2": student_2,
                "Number of shared papers": int(data["count"]),
                "Shared paper titles": " || ".join(titles),
            }
        )

    summary = pd.DataFrame(
        rows,
        columns=[
            "Student 1",
            "Student 2",
            "Number of shared papers",
            "Shared paper titles",
        ],
    )
    summary.to_csv(output_csv, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Graph construction and plotting
# ---------------------------------------------------------------------------

def short_person_name(name: str) -> str:
    if name in DISPLAY_LABEL_OVERRIDES:
        return DISPLAY_LABEL_OVERRIDES[name]

    normalized = re.sub(r"^Dr\s+", "", name).strip()
    return normalized.split()[0] if normalized else name


def filled_label(value: str, width: int = 12) -> str:
    value = str(value).strip()
    return wrap_label(value, width)


def wrap_label(text: str, width: int) -> str:
    lines = []
    for line in str(text).splitlines():
        wrapped = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=True,
        )
        lines.extend(wrapped or [""])
    return "\n".join(lines)


def build_graph(
    coauthorships: dict[tuple[str, str], dict[str, object]],
    vahid_student_papers: dict[str, list[str]],
    include_project_collaborators: bool,
) -> nx.MultiGraph:
    graph = nx.MultiGraph()

    graph.add_node(
        VAHID_NODE,
        kind="vahid",
        label="Vahid",
        node_size=NODE_SIZES["vahid"],
    )

    for student in STUDENTS:
        graph.add_node(
            student.name,
            kind=student.status,
            label=short_person_name(student.name),
            node_size=NODE_SIZES["student"],
        )

        paper_titles = vahid_student_papers.get(student.name, [])
        if paper_titles:
            total_papers = len(paper_titles)
            for paper_index, paper_title in enumerate(paper_titles):
                graph.add_edge(
                    VAHID_NODE,
                    student.name,
                    kind="vahid_paper",
                    title=paper_title,
                    paper_index=paper_index,
                    paper_count=total_papers,
                    layout_weight=1.7 + min(total_papers, 12) * 0.08,
                )
        elif SHOW_SUPERVISION_FALLBACK_FOR_ZERO_PAPER_STUDENTS:
            graph.add_edge(
                VAHID_NODE,
                student.name,
                kind="supervision_fallback",
                layout_weight=0.85,
            )

    for (student_1, student_2), data in coauthorships.items():
        weight = int(data["count"])
        graph.add_edge(
            student_1,
            student_2,
            kind="coauthorship",
            weight=weight,
            titles=data["titles"],
            layout_weight=0.8 + min(weight, 8) * 0.25,
        )

    for student in STUDENTS:
        if student.status == "graduate":
            role_text = GRADUATE_CURRENT_ROLES.get(student.name, "").strip()
            if role_text:
                role_node = f"role::{student.name}"
                graph.add_node(
                    role_node,
                    kind="role",
                    parent=student.name,
                    label=filled_label(role_text, width=13),
                    node_size=NODE_SIZES["role"],
                )
                graph.add_edge(
                    student.name,
                    role_node,
                    kind="role",
                    layout_weight=0.4,
                )

        if include_project_collaborators and student.status == "current":
            collaborator_text = CURRENT_STUDENT_COLLABORATORS.get(
                student.name,
                "",
            ).strip()
            if not collaborator_text:
                continue

            collaborator_node = f"collaborator::{student.name}"
            graph.add_node(
                collaborator_node,
                kind="collaborator",
                parent=student.name,
                label=filled_label(collaborator_text, width=10),
                node_size=NODE_SIZES["collaborator"],
            )
            graph.add_edge(
                student.name,
                collaborator_node,
                kind="collaborator",
                layout_weight=0.25,
            )

    return graph


def initial_student_positions() -> dict[str, tuple[float, float]]:
    positions = {VAHID_NODE: (0.0, 0.0)}
    radius = 6.3

    for index, student in enumerate(STUDENTS):
        angle = (2.0 * math.pi * index / len(STUDENTS)) + math.pi / 2.0
        positions[student.name] = (radius * math.cos(angle), radius * math.sin(angle))

    return positions


def compute_layout(graph: nx.MultiGraph) -> dict[str, tuple[float, float]]:
    """Lay out Vahid and students first, then place leaf nodes radially."""
    people_nodes = [VAHID_NODE] + [student.name for student in STUDENTS]
    people_node_set = set(people_nodes)
    people_graph = nx.Graph()
    people_graph.add_nodes_from(people_nodes)
    start_pos = initial_student_positions()

    for student in STUDENTS:
        edge_data = graph.get_edge_data(VAHID_NODE, student, default={})
        paper_count = sum(
            1 for data in edge_data.values() if data.get("kind") == "vahid_paper"
        )
        has_fallback = any(
            data.get("kind") == "supervision_fallback" for data in edge_data.values()
        )
        people_graph.add_edge(
            VAHID_NODE,
            student.name,
            layout_weight=0.7 + min(paper_count, 12) * 0.12 + (0.45 if has_fallback else 0),
        )

    for source, target, data in graph.edges(data=True):
        if (
            source in people_node_set
            and target in people_node_set
            and data.get("kind") == "coauthorship"
        ):
            people_graph.add_edge(
                source,
                target,
                layout_weight=data.get("layout_weight", 1.0),
            )

    if LAYOUT == "kamada_kawai":
        pos = nx.kamada_kawai_layout(
            people_graph,
            pos=start_pos,
            weight="layout_weight",
        )
        vahid_x, vahid_y = pos[VAHID_NODE]
        pos = {node: (xy[0] - vahid_x, xy[1] - vahid_y) for node, xy in pos.items()}
    else:
        pos = nx.spring_layout(
            people_graph,
            pos=start_pos,
            fixed=[VAHID_NODE],
            seed=LAYOUT_SEED,
            iterations=700,
            k=2.7,
            weight="layout_weight",
        )

    pos[VAHID_NODE] = (0.0, 0.0)
    adjust_people_spacing(pos)

    # Keep role/collaborator nodes near their student but outside the
    # main person network, so they do not distort the co-authorship layout.
    for node, data in graph.nodes(data=True):
        kind = data.get("kind")
        if kind not in {"role", "collaborator"}:
            continue

        parent = data["parent"]
        parent_kind = graph.nodes[parent].get("kind")
        parent_x, parent_y = pos[parent]
        length = math.hypot(parent_x, parent_y) or 1.0
        radial_x, radial_y = parent_x / length, parent_y / length
        tangent_x, tangent_y = -radial_y, radial_x

        if kind == "role":
            radial_distance = 2.35 if parent_kind == "graduate" else 1.95
            tangent_distance = 1.45 if parent_kind == "graduate" else 0.42
        else:
            radial_distance = 3.75 if parent_kind == "graduate" else 3.15
            tangent_distance = -0.72 if parent_kind == "graduate" else -0.48

        pos[node] = (
            parent_x + radial_x * radial_distance + tangent_x * tangent_distance,
            parent_y + radial_y * radial_distance + tangent_y * tangent_distance,
        )

    resolve_leaf_overlaps(graph, pos)

    return pos


def adjust_people_spacing(pos: dict[str, tuple[float, float]]) -> None:
    """Balance the sparse current-student side and the crowded graduate side."""
    left_current_students = [
        student.name
        for student in STUDENTS
        if student.status == "current" and pos[student.name][0] < -2.0
    ]
    graduate_students = [
        student.name for student in STUDENTS if student.status == "graduate"
    ]

    scale_positions(
        pos,
        graduate_students,
        center=(0.0, 0.0),
        factor=GRADUATE_SPREAD_FACTOR,
    )

    if left_current_students:
        centroid_x = sum(pos[name][0] for name in left_current_students) / len(
            left_current_students
        )
        centroid_y = sum(pos[name][1] for name in left_current_students) / len(
            left_current_students
        )
        scale_positions(
            pos,
            left_current_students,
            center=(centroid_x, centroid_y),
            factor=LEFT_CURRENT_TIGHTEN_FACTOR,
            shift=(LEFT_CURRENT_SHIFT_X, 0.0),
        )


def scale_positions(
    pos: dict[str, tuple[float, float]],
    nodes: list[str],
    center: tuple[float, float],
    factor: float,
    shift: tuple[float, float] = (0.0, 0.0),
) -> None:
    center_x, center_y = center
    shift_x, shift_y = shift

    for node in nodes:
        x, y = pos[node]
        pos[node] = (
            center_x + (x - center_x) * factor + shift_x,
            center_y + (y - center_y) * factor + shift_y,
        )


def resolve_leaf_overlaps(
    graph: nx.MultiGraph,
    pos: dict[str, tuple[float, float]],
    iterations: int = 80,
) -> None:
    """Move role/collab leaf nodes away from nearby circles."""
    leaf_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data.get("kind") in {"role", "collaborator"}
    ]
    main_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data.get("kind") in {"vahid", "current", "graduate"}
    ]

    for _ in range(iterations):
        max_push = 0.0

        for leaf in leaf_nodes:
            leaf_x, leaf_y = pos[leaf]

            for other in main_nodes + leaf_nodes:
                if other == leaf:
                    continue

                other_x, other_y = pos[other]
                dx = leaf_x - other_x
                dy = leaf_y - other_y
                distance = math.hypot(dx, dy)
                other_kind = graph.nodes[other].get("kind")
                min_distance = (
                    1.46 if other_kind in {"vahid", "current", "graduate"} else 1.16
                )

                if distance >= min_distance:
                    continue

                if distance < 1e-9:
                    parent = graph.nodes[leaf].get("parent")
                    parent_x, parent_y = pos.get(parent, (0.0, 0.0))
                    dx = leaf_x - parent_x
                    dy = leaf_y - parent_y
                    distance = math.hypot(dx, dy) or 1.0

                push = (min_distance - distance) * 0.55
                leaf_x += dx / distance * push
                leaf_y += dy / distance * push
                max_push = max(max_push, push)

            pos[leaf] = (leaf_x, leaf_y)

        if max_push < 1e-3:
            break


def edge_records_by_kind(
    graph: nx.MultiGraph,
    kind: str,
) -> list[tuple[str, str, int, dict[str, object]]]:
    return [
        (source, target, key, data)
        for source, target, key, data in graph.edges(keys=True, data=True)
        if data.get("kind") == kind
    ]


def parallel_offset(index: int, count: int) -> float:
    if count <= 1:
        return 0.0

    step = min(0.095, 1.10 / max(count - 1, 1))
    return (index - (count - 1) / 2.0) * step


def draw_straight_edge(
    ax: plt.Axes,
    pos: dict[str, tuple[float, float]],
    source: str,
    target: str,
    color: str,
    width: float,
    linestyle: str = "-",
    alpha: float = 1.0,
    offset: float = 0.0,
    source_offset: float | None = None,
    target_offset: float | None = None,
    zorder: int = 1,
) -> None:
    source_x, source_y = pos[source]
    target_x, target_y = pos[target]
    dx = target_x - source_x
    dy = target_y - source_y
    length = math.hypot(dx, dy) or 1.0
    normal_x = -dy / length
    normal_y = dx / length
    source_offset = offset if source_offset is None else source_offset
    target_offset = offset if target_offset is None else target_offset

    ax.plot(
        [
            source_x + normal_x * source_offset,
            target_x + normal_x * target_offset,
        ],
        [
            source_y + normal_y * source_offset,
            target_y + normal_y * target_offset,
        ],
        color=color,
        linewidth=width,
        linestyle=linestyle,
        alpha=alpha,
        solid_capstyle="round",
        dash_capstyle="round",
        zorder=zorder,
    )


def draw_labels(
    ax: plt.Axes,
    graph: nx.MultiGraph,
    pos: dict[str, tuple[float, float]],
    theme: dict[str, dict[str, str]],
) -> None:
    for node, data in graph.nodes(data=True):
        x, y = pos[node]
        kind = data.get("kind")

        if kind == "vahid":
            fontsize = 22
            weight = "bold"
        elif kind in {"current", "graduate"}:
            fontsize = 15
            weight = "bold"
        else:
            fontsize = 11
            weight = "bold"

        color = theme["font"].get(kind, "#111111")

        ax.text(
            x,
            y,
            data["label"],
            fontsize=fontsize,
            fontweight=weight,
            ha="center",
            va="center",
            color=color,
            zorder=5,
            linespacing=0.95,
        )


def draw_graph(
    graph: nx.MultiGraph,
    output_png: Path,
    output_pdf: Path,
    theme_name: str,
    theme: dict[str, dict[str, str]],
) -> None:
    pos = compute_layout(graph)
    fig, ax = plt.subplots(figsize=(20, 16), facecolor="white")
    ax.set_facecolor("white")

    for source, target, _, data in edge_records_by_kind(graph, "supervision_fallback"):
        draw_straight_edge(
            ax,
            pos,
            source,
            target,
            color=theme["edge"]["supervision_fallback"],
            width=1.3,
            linestyle="-",
            alpha=0.32,
            offset=0.0,
            zorder=1,
        )

    for source, target, _, data in edge_records_by_kind(graph, "vahid_paper"):
        paper_count = int(data.get("paper_count", 1))
        paper_index = int(data.get("paper_index", 0))
        line_offset = parallel_offset(paper_index, paper_count)
        draw_straight_edge(
            ax,
            pos,
            source,
            target,
            color=theme["edge"]["vahid_paper"],
            width=2.0 + min(paper_count, 12) * 0.10,
            linestyle="-",
            alpha=0.74,
            offset=line_offset,
            source_offset=0.0 if source == VAHID_NODE else line_offset,
            target_offset=0.0 if target == VAHID_NODE else line_offset,
            zorder=1,
        )

    for source, target, _, data in edge_records_by_kind(graph, "coauthorship"):
        weight = int(data.get("weight", 1))
        draw_straight_edge(
            ax,
            pos,
            source,
            target,
            color=theme["edge"]["coauthorship"],
            width=2.0 + min(weight, 12) * 0.85,
            linestyle="-",
            alpha=0.84,
            offset=0.0,
            zorder=2,
        )

    for source, target, _, data in edge_records_by_kind(graph, "role"):
        draw_straight_edge(
            ax,
            pos,
            source,
            target,
            color=theme["edge"]["role"],
            width=2.0,
            linestyle="--",
            alpha=0.88,
            offset=0.0,
            zorder=1,
        )

    for source, target, _, data in edge_records_by_kind(graph, "collaborator"):
        draw_straight_edge(
            ax,
            pos,
            source,
            target,
            color=theme["edge"]["collaborator"],
            width=2.0,
            linestyle=":",
            alpha=0.88,
            offset=0.0,
            zorder=1,
        )

    for kind in ["role", "collaborator", "current", "graduate", "vahid"]:
        nodes = [
            node for node, data in graph.nodes(data=True) if data.get("kind") == kind
        ]
        if not nodes:
            continue

        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=nodes,
            node_size=[graph.nodes[node]["node_size"] for node in nodes],
            node_color=[theme["node"][kind] for _ in nodes],
            edgecolors=theme.get("node_edge", "white"),
            linewidths=2.0 if kind in {"role", "collaborator"} else 2.8,
            alpha=0.98,
            ax=ax,
        )

    draw_labels(ax, graph, pos, theme)

    legend_items = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=theme["node"]["current"],
            markeredgecolor=theme.get("node_edge", "white"),
            markersize=18,
            label="Current student",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=theme["node"]["graduate"],
            markeredgecolor=theme.get("node_edge", "white"),
            markersize=18,
            label="Graduate",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=theme["node"]["role"],
            markeredgecolor=theme.get("node_edge", "white"),
            markersize=14,
            label="Role",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=theme["node"]["collaborator"],
            markeredgecolor=theme.get("node_edge", "white"),
            markersize=14,
            label="Collaborator",
        ),
        Line2D(
            [0],
            [0],
            color=theme["edge"]["vahid_paper"],
            lw=3.0,
            linestyle="-",
            label="First author",
        ),
        Line2D(
            [0],
            [0],
            color=theme["edge"]["coauthorship"],
            lw=5.0,
            linestyle="-",
            label="Co-authorship",
        ),
    ]

    ax.legend(
        handles=legend_items,
        loc="lower left",
        bbox_to_anchor=(0.035, 0.035),
        frameon=False,
        fontsize=10.5,
        labelspacing=0.72,
    )

    ax.axis("off")
    ax.margins(0.055)
    fig.tight_layout(pad=0.05)

    fig.savefig(output_png, dpi=450, bbox_inches="tight", facecolor="white")
    fig.savefig(output_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------------------------

def parse_sheet_name(value: str) -> object:
    return int(value) if value.isdigit() else value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Vahid publication and collaboration network outputs."
    )
    parser.add_argument(
        "--input",
        default=str(INPUT_FILE),
        help="Path to publication CSV/XLSX file.",
    )
    parser.add_argument(
        "--sheet",
        default=str(SHEET_NAME),
        help="Excel sheet name or zero-based sheet index. Ignored for CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for PNG, PDF, and summary CSV outputs.",
    )
    parser.add_argument(
        "--no-project-collaborators",
        action="store_true",
        help="Hide current-student collaborator nodes to reduce clutter.",
    )
    parser.add_argument(
        "--require-vahid",
        action="store_true",
        help="Only count student co-authorships on papers where Vahid is matched.",
    )
    parser.add_argument(
        "--include-student-later-author-lines",
        action="store_true",
        help=(
            "Also draw Vahid-student paper lines when the student is a later author."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    alias_lookup = build_alias_lookup()
    publications = read_publications(input_file, parse_sheet_name(args.sheet))
    coauthorships, vahid_student_papers, diagnostics = extract_coauthorships(
        publications,
        alias_lookup,
        require_vahid=args.require_vahid or REQUIRE_VAHID_ON_PAPER_FOR_COAUTHORSHIP,
        require_student_first_author_for_edges=(
            REQUIRE_STUDENT_FIRST_AUTHOR_FOR_VAHID_STUDENT_LINES
            and not args.include_student_later_author_lines
        ),
    )

    output_csv = output_dir / OUTPUT_SUMMARY_CSV

    write_coauthorship_summary(coauthorships, output_csv)
    graph = build_graph(
        coauthorships,
        vahid_student_papers,
        include_project_collaborators=(
            INCLUDE_PROJECT_COLLABORATORS and not args.no_project_collaborators
        ),
    )

    written_outputs = []
    for theme_name in COLOR_THEME_ORDER:
        theme = COLOR_THEMES[theme_name]
        output_png = output_dir / f"{OUTPUT_PREFIX}_{theme_name}.png"
        output_pdf = output_dir / f"{OUTPUT_PREFIX}_{theme_name}.pdf"
        draw_graph(graph, output_png, output_pdf, theme_name, theme)
        written_outputs.extend([output_png, output_pdf])

    print("Finished.")
    print(f"Read publication rows: {diagnostics['rows']}")
    print(f"Papers with Vahid matched: {diagnostics['papers_with_vahid']}")
    print(f"Papers with any listed PhD student matched: {diagnostics['papers_with_any_student']}")
    print(
        "Papers with first-author student coauthor links: "
        f"{diagnostics['papers_with_student_pairs']}"
    )
    print(f"Vahid-student paper lines: {diagnostics['vahid_student_paper_edges']}")
    print(f"First-author student co-authorship pairs: {len(coauthorships)}")
    for output_path in written_outputs:
        print(f"Wrote: {output_path}")
    print(f"Wrote: {output_csv}")


if __name__ == "__main__":
    main()

"""
Pins the Markdown table `tabulate` lays out, its bolded header, its one rule
line, and each cell as `str` writes it with each `|` escaped.
"""

from squirtl.markdown.tables import tabulate


def test_a_pipe_inside_a_cell_is_escaped_so_its_row_keeps_one_column_per_header():
    """
    Pins that each `|` a header or a cell holds, inside a code span or
    outside one, is written as `\\|`, so the row splits into no extra
    column.
    """
    assert tabulate(("A|B",), (("`x | y`",), ("a|b|c",))) == (
        "| **A\\|B** |\n|---|\n| `x \\| y` |\n| a\\|b\\|c |"
    )


def test_a_table_bolds_its_header_over_one_rule_and_a_line_per_row():
    """
    Pins the bolded header, the rule of one `---` cell per column, and a
    line per row holding each cell as `str` writes it, a number and an empty
    cell included.
    """
    assert tabulate(("Name", "Count"), (("`a`", 1), ("", 2.5))) == (
        "| **Name** | **Count** |\n|---|---|\n| `a` | 1 |\n|  | 2.5 |"
    )


def test_a_table_with_no_rows_holds_its_header_and_rule_alone():
    """
    Pins that a table given no rows lays out its header and rule alone.
    """
    assert tabulate(("Name",), ()) == "| **Name** |\n|---|"

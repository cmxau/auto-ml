import pytest

from app.services.pipeline_service import _has_cycle, validate_graph


def make_nodes(*ids):
    return [{"id": i, "node_type": "cleaning"} for i in ids]


def make_edge(src, tgt):
    return {"source_node_id": src, "target_node_id": tgt}


# ---- _has_cycle ----

def test_no_cycle_empty_graph():
    assert not _has_cycle([], [])


def test_no_cycle_single_node():
    assert not _has_cycle(["A"], [])


def test_no_cycle_linear_chain():
    assert not _has_cycle(
        ["A", "B", "C"],
        [make_edge("A", "B"), make_edge("B", "C")],
    )


def test_no_cycle_diamond():
    assert not _has_cycle(
        ["A", "B", "C", "D"],
        [make_edge("A", "B"), make_edge("A", "C"),
         make_edge("B", "D"), make_edge("C", "D")],
    )


def test_cycle_self_loop():
    assert _has_cycle(["A"], [make_edge("A", "A")])


def test_cycle_two_nodes():
    assert _has_cycle(
        ["A", "B"],
        [make_edge("A", "B"), make_edge("B", "A")],
    )


def test_cycle_three_nodes():
    assert _has_cycle(
        ["A", "B", "C"],
        [make_edge("A", "B"), make_edge("B", "C"), make_edge("C", "A")],
    )


# ---- validate_graph ----

def test_validate_empty_pipeline_is_invalid():
    result = validate_graph([], [])
    assert not result["valid"]
    assert len(result["errors"]) > 0


def test_validate_single_node_no_edges_is_valid():
    result = validate_graph(make_nodes("A"), [])
    assert result["valid"]
    assert result["errors"] == []


def test_validate_linear_pipeline_is_valid():
    nodes = make_nodes("A", "B", "C")
    edges = [make_edge("A", "B"), make_edge("B", "C")]
    result = validate_graph(nodes, edges)
    assert result["valid"]


def test_validate_cycle_is_invalid():
    nodes = make_nodes("A", "B")
    edges = [make_edge("A", "B"), make_edge("B", "A")]
    result = validate_graph(nodes, edges)
    assert not result["valid"]
    assert any("cycle" in e.lower() for e in result["errors"])


def test_validate_dangling_edge_source_is_invalid():
    nodes = make_nodes("A")
    edges = [make_edge("GHOST", "A")]
    result = validate_graph(nodes, edges)
    assert not result["valid"]


def test_validate_dangling_edge_target_is_invalid():
    nodes = make_nodes("A")
    edges = [make_edge("A", "GHOST")]
    result = validate_graph(nodes, edges)
    assert not result["valid"]

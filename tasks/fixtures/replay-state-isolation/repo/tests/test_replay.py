from replay import Projector


def test_idempotent_within_one_projector():
    p = Projector()
    p.handle("e1", 10)
    p.handle("e1", 10)  # same id -> ignored
    p.handle("e2", 5)
    assert p.total == 15


def test_two_projectors_are_independent():
    a = Projector()
    a.handle("e1", 10)
    b = Projector()
    b.handle("e1", 7)  # different projector must NOT dedup against a
    assert b.total == 7


def test_fresh_projector_starts_empty():
    a = Projector()
    a.handle("e9", 1)
    b = Projector()
    assert b.total == 0

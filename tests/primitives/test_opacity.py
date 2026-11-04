"""Tests for object opacity."""

import pytest

from anima.primitives.group import Group
from anima.primitives.mesh import Mesh


def make_mesh() -> Mesh:
    mesh = Mesh()
    mesh.set_mesh([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    return mesh


def test_opacity_round_trip():
    mesh = make_mesh()
    mesh.set_opacity(0.3)
    assert mesh.opacity == pytest.approx(0.3)
    mesh.opacity = 0.8
    assert mesh.opacity == pytest.approx(0.8)


def test_rgba_alpha_is_the_object_opacity():
    mesh = make_mesh()
    mesh.set_color((0.2, 0.4, 0.6, 0.3))
    assert mesh.opacity == pytest.approx(0.3)
    assert mesh.color == pytest.approx((0.2, 0.4, 0.6, 0.3))
    mesh.set_color((0.8, 0.7, 0.6))
    assert mesh.opacity == pytest.approx(0.3)


def test_rgba_and_opacity_cannot_both_be_supplied():
    mesh = make_mesh()
    with pytest.raises(ValueError):
        mesh.set_material_properties(color=(0.2, 0.4, 0.6, 0.3), opacity=0.8)


def test_set_opacity_returns_the_object():
    mesh = make_mesh()
    assert mesh.set_opacity(0.5) is mesh


def test_opacity_applies_to_descendants():
    children = [make_mesh(), make_mesh()]
    group = Group(children)
    group.set_opacity(0.4)
    assert [c.opacity for c in children] == [pytest.approx(0.4)] * 2


def test_object_without_data_has_no_opacity():
    assert Group().opacity is None

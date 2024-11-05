#!/usr/bin/env python3

# SPDX-License-Identifier: GPL-2.0+ OR BSD-2-Clause

import numpy as np
from jax.tree_util import tree_flatten, tree_map
import pytest


from nifty8.re.multi_grid.indexing import Grid, HEALPixGrid, OGrid, FlatGrid, SparseGrid

pmp = pytest.mark.parametrize


def grid_at(grid, id=None, nbr=None):
    params = []
    for lvl in range(grid.depth + 1):
        ga = grid.at(lvl)
        sz = ga.size
        nd = ga.ndim
        if id is None:
            id = np.array(
                [
                    np.random.randint(0, 1),
                ]
                * nd
            )
        if lvl != grid.depth:
            ch = ga.children(id)
        else:
            ch = None
        if nbr is None:
            nbr = (3,) * nd
        nbrs = ga.neighborhood(id, nbr)
        params.append((sz, nd, ch, nbrs))

        if lvl != 0:
            g_ap = grid.at(lvl - 1)
            children = g_ap.children(id)
            parents = ga.parent(children)
            nextra = parents.ndim - id.ndim
            sl = (slice(None),) * id.ndim + (np.newaxis,) * nextra
            assert np.all(parents == id[sl])

    return params


@pmp(
    "shape0, splits",
    [(3, 2), ((3,), (2, 4)), ((2, 3), ((2,) * 2, (2,) * 2)), ((1, 2, 3), ())],
)
def test_Grid(shape0, splits):
    g = Grid(shape0=shape0, splits=splits)
    if isinstance(splits, int):
        splits = (splits,)
    assert g.depth == len(splits)

    params = grid_at(g)

    if len(splits) > 1:
        sp0 = splits[:1]
        sp1 = splits[1:]
        gn = Grid(shape0=shape0, splits=sp0)
        gn = gn.amend(sp1)
        paramsn = grid_at(gn)
        valid = tree_map(lambda a, b: np.all(a == b), params, paramsn)
        assert np.all(tree_flatten(valid)[0])


@pmp("nside0", [1, 2, 16, 128])
@pmp("depth", [0, 1, 4, 7])
def test_HEALPixGrid(nside0, depth):
    g = HEALPixGrid(nside0=nside0, depth=depth)

    assert g.depth == depth
    gn = HEALPixGrid(nside0=nside0, depth=depth + 2)
    paramsn = grid_at(gn, nbr=(9,))

    g = g.amend(added_depth=2)
    params = grid_at(g, nbr=(9,))
    valid = tree_map(lambda a, b: np.all(a == b), params, paramsn)
    assert np.all(tree_flatten(valid)[0])


# TODO more tests and input variety
def test_OGrid():
    g1 = Grid(shape0=(3,), splits=(2,) * 3)
    g2 = HEALPixGrid(nside0=4, depth=3)
    g3 = Grid(shape0=(3, 5), splits=((1, 2),) * 3)
    g = OGrid(g1, g2, g3)
    grid_at(g, nbr=(3, 9, 2, 3))


@pmp(
    "grid",
    [
        Grid(shape0=(3,), splits=(2,) * 3),
        HEALPixGrid(nside0=8, depth=2),
        Grid(shape0=(3, 2), splits=((2,) * 2,) + ((2, 3),) * 4),
    ],
)
@pmp("ordering", ["serial", "nest"])
def test_FlatGrid(grid, ordering):
    g = FlatGrid(grid, ordering=ordering)

    grid_at(g, nbr=(9,) * grid.at(0).ndim)


# TODO more tests and input variety
def test_SparseGrid():
    mapping = (np.arange(10), np.arange(6))
    g = Grid(shape0=(10,), splits=(2,))
    g = SparseGrid(g, mapping)
    grid_at(g, nbr=(3,))
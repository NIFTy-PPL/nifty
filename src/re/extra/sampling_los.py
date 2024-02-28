#!/usr/bin/env python3

# SPDX-License-Identifier: GPL-2.0+ OR BSD-2-Clause

import dataclasses
from functools import partial

import jax
from jax import numpy as jnp

from ..tree_math import ShapeWithDtype
from ..model import Model


def _los(x, /, start, end, *, distances, shape, n_sampling_points, order=1):
    from jax.scipy.ndimage import map_coordinates

    l2i = ((shape - 1) / shape) / distances
    start_iloc = start * l2i
    end_iloc = end * l2i
    ddi = (end_iloc - start_iloc) / n_sampling_points
    adi = jnp.arange(0, n_sampling_points) + 0.5
    dist = jnp.linalg.norm(end - start)
    pp = start_iloc[:, jnp.newaxis] + ddi[:, jnp.newaxis] * adi[jnp.newaxis]
    return map_coordinates(x, pp, order=order, cval=jnp.nan).sum() * (
        dist / n_sampling_points
    )


class SamplingCartesianGridLOS(Model):
    start: jax.Array = dataclasses.field(metadata=dict(static=False))
    end: jax.Array = dataclasses.field(metadata=dict(static=False))
    distances: jax.Array = dataclasses.field(metadata=dict(static=False))

    def __init__(
        self,
        start,
        end,
        *,
        distances,
        shape,
        dtype=None,
        n_sampling_points=500,
        interpolation_order=1,
    ):
        # We assume that `start` and `end` are of shape (n_points, n_dimensions)
        self.start = jnp.array(start)
        self.end = jnp.array(end)
        self.distances = jnp.array(distances)
        self._los = partial(
            _los,
            n_sampling_points=n_sampling_points,
            order=interpolation_order,
            distances=self.distances,
            shape=jnp.array(shape),
        )
        super().__init__(
            domain=ShapeWithDtype(shape, dtype), target=ShapeWithDtype(end.shape, dtype)
        )

    def __call__(self, x):
        in_axes = (None, 0, 0)
        if self.start.ndim < self.end.ndim:
            in_axes = (None, None, 0)
        elif self.start.ndim > self.end.ndim:
            in_axes = (None, 0, None)
        return jax.vmap(self._los, in_axes=in_axes)(x, self.start, self.end)
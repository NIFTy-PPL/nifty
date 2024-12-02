# %%
from dataclasses import field
from functools import partial

import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt

import nifty8.re as jft
from nifty8.re.multi_grid.indexing import Grid, OpenGrid
from nifty8.re.multi_grid.kernel import ICRefine, _FrozenKernel
from nifty8.re.tree_math import ShapeWithDtype


def matern_kernel(x, y, scale=1.0, cutoff=1.0, dof=1.5):
    distance = jnp.linalg.norm(x - y, axis=0)
    if dof == 0.5:
        cov = scale**2 * jnp.exp(-distance / cutoff)
    elif dof == 1.5:
        reg_dist = jnp.sqrt(3) * distance / cutoff
        cov = scale**2 * (1 + reg_dist) * jnp.exp(-reg_dist)
    elif dof == 2.5:
        reg_dist = jnp.sqrt(5) * distance / cutoff
        cov = scale**2 * (1 + reg_dist + reg_dist**2 / 3) * jnp.exp(-reg_dist)
    else:
        raise NotImplementedError()
    # NOTE, this is not safe for differentiating because `cov` still may
    # contain NaNs
    return jnp.where(distance < 1e-8 * cutoff, scale**2, cov)


class ICRCorrelate(jft.Model):
    frozen_kernel: _FrozenKernel = field(metadata=dict(static=False))

    def __init__(
        self,
        grid: Grid,
        covariance: callable,
        *,
        window_size,
        rtol=1e-5,
        atol=1e-5,
        buffer_size=1000,
        use_distances=True,
        prefix="icr",
    ):
        self.covariance = covariance
        self.grid = grid

        self.kernel = ICRefine(grid, covariance, window_size=window_size)
        self.frozen_kernel = self.kernel.freeze(
            rtol=rtol, atol=atol, buffer_size=buffer_size, use_distances=use_distances
        )

        self.window_size = window_size
        self._name = str(prefix) + "xi"

        shapes = [
            ShapeWithDtype(self.grid.at(lvl).shape, jnp.float_)
            for lvl in range(grid.depth + 1)
        ]
        super().__init__(domain={self._name: shapes}, white_init=True)

    def __call__(self, x):
        return self.frozen_kernel(x[self._name])[-1]


# %%
depth = 2
shape = (32, 32)
splits = 2

window_size = 3
padding = window_size // 2
shape0 = tuple(int(s / splits**depth + (2 + 2 / splits) * padding) + 1 for s in shape)
grid = OpenGrid(shape0=shape0, splits=(splits,) * depth, padding=(padding,) * depth)

cf = ICRCorrelate(
    grid,
    partial(matern_kernel, scale=1.0, cutoff=1.0, dof=0.5),
    window_size=window_size,
)

# %%
res = cf(cf.init(jax.random.PRNGKey(42)))
plt.imshow(res)
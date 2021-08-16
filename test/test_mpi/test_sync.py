# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright(C) 2021 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

import pytest
from mpi4py import MPI

import nifty7 as ift

from ..common import setup_function, teardown_function

comm = MPI.COMM_WORLD
ntask = comm.Get_size()
rank = comm.Get_rank()
master = (rank == 0)
mpi = ntask > 1

pmp = pytest.mark.parametrize
pms = pytest.mark.skipif


@pms(not mpi, reason="requires at least two mpi tasks")
def test_MPI_equality():
    obj = rank
    with pytest.raises(RuntimeError):
        ift.utilities.check_MPI_equality(obj, comm)

    obj = [ii + rank for ii in range(10, 12)]
    with pytest.raises(RuntimeError):
        ift.utilities.check_MPI_equality(obj, comm)

    sseqs = ift.random.spawn_sseq(2)
    for obj in [12., None, (29, 30), [1, 2, 3], sseqs[0], sseqs]:
        ift.utilities.check_MPI_equality(obj, comm)

    obj = ift.random.spawn_sseq(2, parent=sseqs[comm.rank])
    with pytest.raises(RuntimeError):
        ift.utilities.check_MPI_equality(obj, comm)


@pms(not mpi, reason="requires at least two mpi tasks")
def test_MPI_synced_random_state():
    ift.utilities.check_MPI_synced_random_state(comm)

    if master:
        ift.random.push_sseq_from_seed(123)
    with pytest.raises(RuntimeError):
        ift.utilities.check_MPI_synced_random_state(comm)
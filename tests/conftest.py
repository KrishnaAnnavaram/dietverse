import pytest

from dietverse.data import load_dataset
from dietverse.synthetic import write_synthetic


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory):
    return write_synthetic(tmp_path_factory.mktemp("diet"), n_countries=50, seed=5)


@pytest.fixture(scope="session")
def ds(data_dir):
    return load_dataset(data_dir)

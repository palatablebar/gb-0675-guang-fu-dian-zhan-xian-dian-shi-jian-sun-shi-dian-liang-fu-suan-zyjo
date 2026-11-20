import pytest
from app.engine import evaluate
from app.config import ROOT
@pytest.fixture
def sample():
    return evaluate()
@pytest.fixture
def clean():
    return evaluate({'dataset':'clean'})

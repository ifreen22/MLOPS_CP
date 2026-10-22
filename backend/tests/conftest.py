import os
import matplotlib
matplotlib.use("Agg")
from types import SimpleNamespace
import pytest

# Ensure environment variables are loaded for all tests
os.environ["JWT_SECRET"] = "fKR6nhgSIUaf6Q7pMO6p7hlnmol0oTmDDKU95yrVhcU"
os.environ["AGENT_API_TOKEN"] = "x3Rxw2keZYcsthfajgRG7Y1OmopSfD6zrfNfB5VfDtg"
os.environ["ADMIN_PASSWORD"] = "caXK6HxqFUVS5buIi1ayl2wEA2w4kTsI8rtuCRj_9rA"
os.environ["ADMIN_EMAIL"] = "admin@localhost"

from app.main import app
from app.core.auth import get_current_user
from app.api.v1.controllers import system_controller

default_test_user = SimpleNamespace(
    id="test-user",
    email="admin@example.test",
    organizationId="test-organization",
    role="ADMIN",
    firstName="Test",
    lastName="Admin",
)

@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    system_controller.last_telemetry = None
    app.dependency_overrides[get_current_user] = lambda: default_test_user
    yield
    system_controller.last_telemetry = None
    app.dependency_overrides[get_current_user] = lambda: default_test_user

from usm.core.health import HealthChecker
from usm.models import Skill, Transport

def test_health_check_python_resolved():
    skill = Skill(
        id="py-tool",
        name="Python Tool",
        transport=Transport.STDIO,
        command="python",
        args=["-c", "print('hello')"]
    )
    res = HealthChecker.check_skill(skill)
    assert res.status == "healthy"
    assert res.command_resolved is True
    assert res.resolved_path is not None

def test_health_check_missing_command():
    skill = Skill(
        id="fake-tool",
        name="Fake Tool",
        transport=Transport.STDIO,
        command="non_existent_command_12345_xyz"
    )
    res = HealthChecker.check_skill(skill)
    assert res.status == "warning"
    assert res.command_resolved is False

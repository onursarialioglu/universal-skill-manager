from usm.core.portability import PortabilityManager
from usm.models import Skill, Transport
from usm.registry import RegistryManager

def test_export_and_import_profile(tmp_path, temp_usm_home):
    reg_mgr = RegistryManager()
    sk = Skill(
        id="exported-srv",
        name="Exported Server",
        transport=Transport.STDIO,
        command="npx",
        args=["pkg"]
    )
    reg_mgr.add_skill(sk)

    pack_file = tmp_path / "backup.usmpack"
    exported_path = PortabilityManager.export_profile(pack_file)
    assert exported_path.exists()

    # Now remove from registry
    reg_mgr.remove_skill("exported-srv")
    assert reg_mgr.get_skill("exported-srv") is None

    # Import back
    count = PortabilityManager.import_profile(exported_path)
    assert count == 1
    imported_sk = reg_mgr.get_skill("exported-srv")
    assert imported_sk is not None
    assert imported_sk.name == "Exported Server"

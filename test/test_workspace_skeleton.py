from pathlib import Path


REQUIRED_PACKAGES = (
    'orbinspect_interfaces',
    'orbinspect_description',
    'orbinspect_gazebo',
    'orbinspect_dynamics',
    'orbinspect_control',
    'orbinspect_safety',
    'orbinspect_guidance',
    'orbinspect_perception',
    'orbinspect_mission',
    'orbinspect_eval',
    'orbinspect_bringup',
    'orbinspect_utils',
)


def test_required_packages_have_manifest() -> None:
    workspace_root = Path(__file__).resolve().parents[1]

    for package_name in REQUIRED_PACKAGES:
        package_root = workspace_root / 'src' / package_name

        assert package_root.is_dir()
        assert (package_root / 'package.xml').is_file()
        assert (package_root / 'README.md').is_file()

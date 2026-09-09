from orbinspect_mission.state_machine import MissionState
from orbinspect_mission.state_machine import MissionStateMachine


def test_state_machine_reaches_complete() -> None:
    machine = MissionStateMachine()

    assert machine.start() == MissionState.RUNNING
    assert machine.waypoint_reached() == MissionState.WAYPOINT_REACHED
    assert machine.resume() == MissionState.RUNNING
    assert machine.coverage_complete() == MissionState.COVERAGE_COMPLETE
    assert machine.complete() == MissionState.COMPLETE

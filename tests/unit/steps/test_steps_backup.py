from unittest.mock import MagicMock, patch

from cou.steps.backup import backup


def test_backup():
    with patch("cou.steps.backup.logging.info") as log, patch(
        "cou.steps.backup.model"
    ) as model, patch("cou.steps.backup.get_database_app"):
        model.run_action_on_leader = MagicMock()
        model.scp_from_unit = MagicMock()
        model.get_unit_from_name = MagicMock()

        backup()
        assert log.call_count == 5

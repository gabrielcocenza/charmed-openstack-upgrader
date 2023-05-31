from argparse import Namespace

from cou.steps import UpgradeStep
from cou.steps.backup import backup


def plan(args: Namespace) -> UpgradeStep:
    plan = UpgradeStep(description="Top level plan", parallel=False, function=None)
    plan.add_step(
        UpgradeStep(description="backup mysql databases", parallel=False, function=backup))
    return plan

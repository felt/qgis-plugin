# -*- coding: utf-8 -*-
"""Multi-step feedback proxy

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2022 by Nyall Dawson'
__date__ = '22/11/2022'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import (
    Qt
)

from qgis.core import QgsFeedback


class MultiStepFeedback(QgsFeedback):
    """
    Handles smooth progress reporting for multi-step tasks
    """

    def __init__(self, steps: int, feedback: QgsFeedback):
        """
        Constructor for MultiStepFeedback, for a process with the specified
        number of steps. This feedback object will proxy calls
        to the specified feedback object.
        """
        super().__init__()
        self.steps = steps
        self.current_step = 0
        self._feedback = feedback

        self._feedback.canceled.connect(self.cancel, Qt.DirectConnection)
        self.progressChanged.connect(self._update_overall_progress)

    def step_finished(self):
        """
        Call to increment the current step number
        """
        self.set_current_step(self.current_step + 1)

    def set_current_step(self, step: int):
        """
        Sets the step which is being executed. This is used
        to scale the current progress to account for progress
        through the overall process.
        """
        self.current_step = step
        self._feedback.setProgress(
            100 * (self.current_step / self.steps)
        )

    def _update_overall_progress(self, progress: float):
        """
        Updates the overall progress when the current step progress
        changes
        """
        base_progress = 100.0 * self.current_step / self.steps
        current_step_progress = progress / self.steps
        self._feedback.setProgress(base_progress + current_step_progress)

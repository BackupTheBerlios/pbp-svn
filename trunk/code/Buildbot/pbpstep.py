from buildbot.process import step
from buildbot.status import event

import re
import os

class PBP(step.ShellCommand):
    flunkOnFailure = True
    name = "pbp"

    def __init__(self, filename=None, **kwargs):
        if not filename:
            raise TypeError("please pass a .tests file")
        command = "python run_pbpscript %s" % (filename,)
        self.statusName = "pbp %s" % (os.path.basename(filename),)
        step.ShellCommand.__init__(self, command=command, **kwargs)

    def startStatus(self):
        evt_text = "running %s" % (self.statusName,)
        evt = event.Event("yellow", evt_text.split(),
                          files={'log':self.log})
        self.setCurrentActivity(evt)

    def finished(self, rc):
        self.failures = 0
        self.successes = 0
        if rc:
            self.failures = 1
        output = self.log.getAll()
        self.failures += len(re.findall('\*\*\* .*FAILURE: (.*)\*\*\*', output))
        self.successes += len(re.findall('\nSUCCESS: ', output))


        result = (step.SUCCESS, [str(self.successes), self.statusName, 'passed'])

        total = self.failures + self.successes

        if self.failures:
            result = (step.FAILURE, ['%s/%s' % (self.failures, total),
                                     self.statusName,
                                     'failures'])

        return self.stepComplete(result)

    def finishStatus(self, result):
        tot = self.failures + self.successes
        if self.failures:
            color = "red"
            text = ("%s/%s %s tests failed" % (self.failures, tot, self.statusName)).split()
        else:
            color = "green"
            text = ("%s tests succeeded" % (self.successes)).split()
        self.updateCurrentActivity(color=color, text=text)
        self.finishStatusSummary()
        self.finishCurrentActivity()

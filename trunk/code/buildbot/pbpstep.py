from buildbot.process import step
from buildbot.status import event

import re

class PBP(step.ShellCommand):
    flunkOnFailure = True
    name = "pbp"

    def __init__(self, directory=None, **kwargs):
        if not directory:
            raise TypeError("please pass testdir")
        command = "bash run_pbpscript %s" % (directory,)
        step.ShellCommand.__init__(self, command=command, **kwargs)

    def startStatus(self):
        evt = event.Event("yellow", "running pbp".split(),
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

        result = (step.SUCCESS, [str(self.successes), 'pbp tests', 'passed'])

        total = self.failures + self.successes

        if self.failures:
            result = (step.FAILURE, ['%s/%s' % (self.failures, total), 'pbp', 
                                     'failures'])

        return self.stepComplete(result)

    def finishStatus(self, result):
        tot = self.failures + self.successes
        if self.failures:
            color = "red"
            text = ("%s/%s tests failed" % (self.failures, tot)).split()
        else:
            color = "green"
            text = ("%s tests succeeded" % (self.successes)).split()
        self.updateCurrentActivity(color=color, text=text)
        self.finishStatusSummary()
        self.finishCurrentActivity()

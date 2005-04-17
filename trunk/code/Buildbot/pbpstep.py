from buildbot.process import step
from buildbot.status import builder

import re
import os

class PBP(step.ShellCommand):
    flunkOnFailure = True
    name = "pbp"

    def __init__(self, filename=None, **kwargs):
        if not filename:
            raise TypeError("please pass a .tests file")
        command = "python run_pbpscript %s" % (filename,)
        self.statusName = "%s" % (os.path.basename(filename),)
        step.ShellCommand.__init__(self, command=command, **kwargs)

    def createSummary(self, log):
        self.failures = 0
        self.successes = 0
        output = log.getText()
        failuretext = re.findall('\*\*\* .*FAILURE: (.*)\*\*\*', output)
        self.failures += len(failuretext)
        self.successes += len(re.findall('\nSUCCESS: ', output))
        if self.failures:
            self.addCompleteLog('failures', '\n'.join(failuretext))


    def getText(self, cmd, results):
        res = ("---- %s %s passed" % (self.successes,
                                     self.statusName)).split()

        total = self.failures + self.successes

        if self.failures:
            res = ('--- %s/%s %s failures' % (self.failures, total, 
                                              self.statusName)).split()

        return self.describe() + res
    def getColor(self, cmd, results):
        if self.failures:
            return 'red'
        return 'green'

#    def finishStatus(self, result):
#        tot = self.failures + self.successes
#        _d = dict(failures=self.failures, total=tot, name=self.statusName,
#                  successes=self.successes)
#        if self.failures:
#            _t = "%(failures)s/%(total)s %(name)s failed" 
#            color = "red"
#        else:
#            _t = "%(successes)s %(name)s succeeded" 
#            color = "green"
#        text = (_t % _d).split()
#        self.updateCurrentActivity(color=color, text=text)
#        self.finishStatusSummary()
#        self.finishCurrentActivity()

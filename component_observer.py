from buildbot.plugins import util
import re


class CurrentComponentObserver(util.LogLineObserver):
    _line_re = re.compile(r'^Need rebuild of ([\w\.]+)/\.$')

    def outLineReceived(self, line):
        m = self._line_re.search(line.strip())
        if m:
            component, result = m.groups()
            self.step.updateSummary('Building %s' % component)

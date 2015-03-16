from buildbot.process.logobserver import LineConsumerLogObserver
from buildbot.process.buildstep import BuildStep, ShellMixin
import re
from twisted.internet import defer


class BuildStep(BuildStep, ShellMixin):
    new_build_re = re.compile(r'^Need rebuild of ([\w\.]+)/\.$')
    finished_build_re = re.compile(r'^Subtask commit build of gnome-continuous/components/([\w\.]+)/x86_64/\.$')
    currentComponent = ''

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        BuildStep.__init__(self, **kwargs)
        self.addLogObserver('stdio', LineConsumerLogObserver(self.logConsumer))

    def getFinalState(self):
        return self.describe(True)

    def getCurrentSummary(self):
        if self.currentComponent:
            return {u'step': u"Building %s" % self.currentComponent}
        else:
            return {u'step': u"Starting"}

    @defer.inlineCallbacks
    def run(self):
        super(BuildStep, self).run()

    def logConsumer(self):
        while True:
            stream, line = yield
            m = self.new_build_re.search(line.strip())
            if m:
                self.currentComponent, result = m.groups()
                self.updateSummary()
            m = self.new_build_re.search(line.strip())
            if m:
                component, result = m.groups()
                log_contents = ''
                with open("local/build/log-%s.txt" % component, 'r') as f:
                    log_contents = f.read()
                self.addCompleteLog('log-%s' % component, log_contents)
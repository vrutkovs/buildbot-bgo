from buildbot.process.logobserver import LineConsumerLogObserver
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source.base import Source
import re


class BuildStep(ShellCommand):
    new_build_re = re.compile(r'Need rebuild of ([\w\.]+)/\.')
    finished_build_re = re.compile(r'Subtask commit build of gnome-continuous/components/([\w\.]+)/x86_64/\.')
    currentComponent = ''

    def __init__(self, **kwargs):
        ShellCommand.__init__(self, **kwargs)
        self.addLogObserver('stdio', LineConsumerLogObserver(self.logConsumer))

    def getCurrentSummary(self):
        if self.currentComponent:
            return {u'step': u"Building %s" % self.currentComponent}
        else:
            return {u'step': u"Starting"}

    def getResultSummary(self):
        return {u'step': u"Done"}

    def logConsumer(self):
        while True:
            stream, line = yield
            m = self.new_build_re.match(line.strip())
            if m is not None:
                self.currentComponent = m.group(0)
                self.updateSummary()
            m = self.new_build_re.match(line.strip())
            if m is not None:
                component = m.group(0)
                log_contents = ''
                with open("local/build/log-%s.txt" % component, 'r') as f:
                    log_contents = f.read()
                self.addCompleteLog('log-%s' % component, log_contents)


class BGOSource(Source):
    def __init__(self, repourl=None, baseURL=None, mode='incremental',
                 method=None, defaultBranch=None, **kwargs):
        pass

    def startVC(self, branch, revision, patch):
        pass

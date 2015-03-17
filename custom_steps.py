from buildbot.changes.base import PollingChangeSource
from buildbot.process.logobserver import LineConsumerLogObserver
from buildbot.util import json
from buildbot.util import ascii2unicode
from buildbot.util.state import StateMixin
from buildbot.steps.shell import ShellCommand
from twisted.internet import defer
from twisted.internet import utils
from twisted.python import log

import re
import os


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


class BGOPoller(PollingChangeSource, StateMixin):
    def __init__(self, workdir=None, pollInterval=5 * 60, pollAtLaunch=False,
                 name='BGOPoller'):
        PollingChangeSource.__init__(self, name=name,
                                     pollInterval=pollInterval,
                                     pollAtLaunch=pollAtLaunch)
        self.lastRev = {}
        self.workdir = workdir

    def activate(self):
        # make our workdir absolute, relative to the master's basedir
        if not os.path.isabs(self.workdir):
            self.workdir = os.path.join(self.master.basedir, self.workdir)

        log.msg("BGOPoller: using workdir '%s'" % self.workdir)
        d = self.getState('lastRev', {})

        def setLastRev(lastRev):
            self.lastRev = lastRev
        d.addCallback(setLastRev)
        d.addCallback(lambda _: PollingChangeSource.activate(self))
        d.addErrback(log.err, 'while initializing BGOPoller')

    def _dovccmd(self, command, path=None):
        d = utils.getProcessOutputAndValue('ostbuild', ['make', '-n'] + command,
                                           path=path, env=os.environ)

        def _convert_nonzero_to_failure(res):
            "utility to handle the result of getProcessOutputAndValue"
            (stdout, stderr, code) = res
            if code != 0:
                raise EnvironmentError('command failed with exit code %d: %s'
                                       % (code, stderr))
            return stdout.strip()
        d.addCallback(_convert_nonzero_to_failure)
        return d

    @defer.inlineCallbacks
    def poll(self):
        log.msg('BGOPoller: running resolve & bdiff')
        yield self._dovccmd(['resolve', 'fetchAll=true'], self.workdir)
        yield self._dovccmd(['bdiff'], self.workdir)
        log.msg('BGOPoller: resolve & bdiff complete')
        bdiff = json.load('local/bdiff.json')
        log.msg('BGOPoller: got bdiff: %s' % bdiff)
        rev = {}
        for change_type in ['added', 'modified', 'removed']:
            if 'gitlog' in bdiff[change_type].keys():
                project = bdiff[change_type]['latest']['name']
                src = bdiff[change_type]['latest']['src']
                gitlog = bdiff[change_type]['gitlog']
                for change in gitlog:
                    rev = change
                    yield self._process_changes(change, project, src)
        self.lastRev = rev
        yield self.setState('lastRev', self.lastRev)

    @defer.inlineCallbacks
    def _process_changes(self, newRev, project, src):
        revision = newRev['Checksum']
        author = newRev['From']
        timestamp = newRev['Date']

        yield self.master.data.updates.addChange(
            author=author,
            revision=revision,
            files=[],
            comments=[],
            when_timestamp=timestamp,
            branch=project,
            category=self.category,
            project=self.project,
            repository=ascii2unicode(src),
            src=u'git')

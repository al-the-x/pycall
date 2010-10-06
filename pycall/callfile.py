#!/usr/bin/python
"""
	pycall.callfile
	~~~~~~~~~~~~~~~

	Implements a `CallFile` class for creating, editing, and spooling Asterisk
	call files.

	:copyright: (c) 2010 by Randall Degges.
	:license: BSD, see LICENSE for more details.
"""


from shutil import move
from time import mktime
from pwd import getpwnam
from tempfile import mkstemp
from datetime import datetime
from os import path, chown, utime, fdopen
from errors import *


class CallFile:
	"""
	Stores and manipulates call file information. Also allows users to schedule
	call files to be spooled.
	"""

	def __init__(
		self, channel=None, trunk_type=None, trunk_name=None, number=None,
		callerid=None, callerid_name=None, callerid_num=None, wait_time=None,
		max_retries=None, retry_time=None, account=None, application=None,
		data=None, context=None, extension=None, priority=None, set_var=None,
		archive=None, user=None, tmpdir=None, filename=None,
		spool_dir=None
	):

		if not spool_dir: spool_dir = '/var/spool/asterisk/outgoing/'

		args = dict(locals())
		args.pop('self')
		for name, value in args.items():
			setattr(self, name, value)

	def _is_valid(self):
		"""
		Checks all current class attributes to ensure that there are no
		lurking problems.

		:return:	True if no problems. False if problems. May raise
					exceptions if necessary.
		"""
		if not (self.channel or (self.trunk_type and self.trunk_name and \
			self.number)):
			raise NoChannelDefinedError

		if not ((self.application and self.data) or \
			(self.context and self.extension and self.priority)):
			raise NoActionDefinedError

		return True

	def _buildfile(self):
		"""
		Use the class attributes to build a call file string.

		:return:	A list which contains one call file directive in each
					element. These can be written to a file.
		"""
		if not self._is_valid():
			raise UnknownError

		cf = []

		if self.channel:
			cf.append('Channel: '+self.channel)
		elif self.trunk_type and self.trunk_name and self.number:
			if self.trunk_type.lower() == 'local':
				cf.append('Channel: %s/%s@%s' % (self.trunk_type, self.number,
					self.trunk_name))
			else:
				cf.append('Channel: %s/%s/%s' % (self.trunk_type,
					self.trunk_name, self.number))
		else:
			raise UnknownError

		if self.application:
			cf.append('Application: '+self.application)
			cf.append('Data: '+self.data)
		elif self.context and self.extension and self.priority:
			cf.append('Context: '+self.context)
			cf.append('Extension: '+self.extension)
			cf.append('Priority: '+self.priority)
		else:
			raise UnknownError

		if self.set_var:
			for var, value in self.set_var.items():
				cf.append('Set: %s=%s' % (var, value))

		if self.callerid:
			cf.append('Callerid: %s' % self.callerid)
		elif self.callerid_name and self.callerid_num:
			cf.append('Callerid: "%s" <%s>' % (self.callerid_name,
				self.callerid_num))
		elif self.callerid_name:
			cf.append('Callerid: "%s"' % self.callerid_name)
		elif self.callerid_num:
			cf.append('Callerid: "" <%s>' % self.callerid_num)

		if self.wait_time:
			cf.append('WaitTime: %s' % self.wait_time)

		if self.max_retries:
			cf.append('Maxretries: %s' % self.max_retries)

		if self.retry_time:
			cf.append('RetryTime: %s' % self.retry_time)

		if self.account:
			cf.append('Account: %s' % self.account)

		if self.archive:
			cf.append('Archive: yes')

		return cf

	@property
	def contents ( self ):
		'''
		A convenience property to fetch the contents of the callfile without
		having to write it to disk. Implemented as a property so as not to
		break the convention of calling the "protected" method "_buildfile"
		directly.
		'''
		return '\n'.join(self._buildfile())


	def _writefile(self, cf):
		"""
		Write a temporary call file.

		:param cf:	List of call file directives.
		:return:	Absolute path name (as a string) to the temporary call
					file.
		"""
		if self.tmpdir:
			file, fname = mkstemp(suffix='.call', dir=self.tmpdir)
		else:
			file, fname = mkstemp('.call')

		with fdopen(file, 'w') as f:
			for line in cf:
				f.write(line+'\n')

		return fname


	def get_filename ( self, filename ):
		"""
		Constructs an appropriate filename for the callfile, based upon
		optional user-supplied information.

		:filename:		The filename to use if none has been specified.
		"""
		if self.filename:
			filename = self.filename

		if not filename.endswith('.call'):
			filename += '.call'

		return path.realpath(self.spool_dir) + '/' + filename


	def run(self, time=None):
		"""
		Uses the class attributes to submit this `CallFile` to the Asterisk
		spooling directory.

		:param time:	[optional] The time (as a python datetime object) to
						submit this `CallFile` to the Asterisk spooling
						directory.
		:return:		True on success. False on failure.
		"""
		fname = self._writefile(self._buildfile())

		if self.user:
			try:
				pwd = getpwnam(self.user)
				uid = pwd[2]
				gid = pwd[3]

				try:
					chown(fname, uid, gid)
				except:
					raise NoUserPermissionError
			except:
				raise NoUserError

		# Change the modification and access time on the file so that Asterisk
		# knows when to place the call. If time is not specified, then we place
		# the call immediately.
		try:
			time = mktime(time.timetuple())
			utime(fname, (time, time))
		except:
			pass

		try:
			move(fname, self.get_filename(path.basename(fname)))
		except:
			raise NoSpoolPermissionError
		return True


if __name__ == '__main__':
	print 'You have successfully installed pycall. Check out our website ' \
		'for more information: http://pycall.org/'


.. include:: ../../global.rst

.. _`libc API`:

***************
libc
***************

The module ``libc`` exports a number of variables, many of which are
operating system-specific and some are computed variables.  Some of
these are "built-in" in :file:`src/libc-wrap.c` and some are
dynamically generated for this platform in :file:`src/libc-api.c`.

``help libc`` will give a complete list of exported names.

Variables defined in module ``libc`` use ``libc``-oriented types,
commonly ``C/int`` and :lname:`C` portable type names such as
``libc/pid_t``.

There are many places where it would be incredibly convenient to pass
in a fixnum rather than the (correct) :lname:`C` base type but I've
tried to resist.  By and large, the values passed *to* :lname:`C`
library functions should be the result of previous interactions with
the :lname:`C` library.  However, there are a few places where it's
allowed!

Common *values* for comparison purposes (read: one's I've needed!),
say, 0 (zero), have been created for use with :lname:`C`-specific
comparators.  Unfortunately, :lname:`C`'s rather easy way with integer
promotion isn't carried over into :lname:`Idio` and to avoid
combinatorial explosion only like types can be compared.  This means
we have multiple zeroes.  ``C/0i``, a ``C/int``, isn't the same base
type as ``C/0u``, a ``C/uint``, which isn't the same type as, say,
``libc/0pid_t``, a zero in the type of a ``libc/pid_t``.

This requires that we can't be as casual as we can in :lname:`C`:

.. code-block:: idio-console

   Idio> C/> (libc/getpid) libc/0pid_t
   #t
   Idio> C/== C/0i (libc/kill (libc/getpid) C/0i)
   #t

If no handy variable exists you can always create one:

.. code-block:: idio-console

   Idio> C/integer-> -1 libc/pid_t
   -1

although, as ``libc/pid_t`` is either directly referencing or part of
a chain of references to a :lname:`C` base type then ``type->string``
can only return the base type.

.. code-block:: idio-console

   Idio> x := C/integer-> -1 libc/pid_t
   -1
   Idio> type->string x
   "C/int"

This is unfortunate as a ``pid_t`` is not an ``int`` on all systems
(although it clearly is on this one).  In other words, the *output* of
``type->string`` is not portable.

Stick to the :lname:`C` API!

Of course, in the particular case of system and standard library
calls, when errors occur a ``^system-error`` condition is raised such
that the system/library call can often be presumed to have succeeded
if you haven't been thrown into a condition handler.

Not all :lname:`C` system or library calls conform to this practice.

Common libc Variables
=====================

:var:`libc/0pid_t`

     :type: ``libc/pid_t``
     :value: 0 (zero)

:var:`libc/0gid_t`

     :type: ``libc/gid_t``
     :value: 0 (zero)

From :file:`fcntl.h`:

:var:`libc/FD_CLOEXEC`

     :type: ``C/int``

:var:`libc/F_DUPFD`

     :type: ``C/int``

:var:`libc/F_DUPFD_CLOEXEC`

     :type: ``C/int``

     .. warning::

	Not all systems define ``F_DUPFD_CLOEXEC``.

:var:`libc/F_GETFD`

     :type: ``C/int``

:var:`libc/F_SETFD`

     :type: ``C/int``

:var:`libc/F_GETFL`

     :type: ``C/int``

:var:`libc/F_SETFL`

     :type: ``C/int``

From :file:`limits.h`:

:var:`libc/CHAR_MAX`

     :type: ``C/char``

:var:`libc/SCHAR_MIN`

     :type: ``C/schar``

:var:`libc/SCHAR_MAX`

     :type: ``C/schar``

:var:`libc/UCHAR_MAX`

     :type: ``C/uchar``

:var:`libc/INT_MIN`

     :type: ``C/int``

:var:`libc/INT_MAX`

     :type: ``C/int``

:var:`libc/UINT_MAX`

     :type: ``C/uint``

:var:`libc/LONG_MIN`

     :type: ``C/long``

:var:`libc/LONG_MAX`

     :type: ``C/long``

:var:`libc/ULONG_MAX`

     :type: ``C/ulong``

:var:`libc/LLONG_MIN`

     :type: ``C/longlong``

:var:`libc/LLONG_MAX`

     :type: ``C/longlong``

:var:`libc/ULLONG_MAX`

     :type: ``C/ulonglong``

From :file:`signal.h`:

:var:`libc/SIG_DFL`

     :type: ``C/pointer``

:var:`libc/SIG_IGN`

     :type: ``C/pointer``

From :file:`stdio.h`:

.. _`libc/BUFSIZ`:

:var:`libc/BUFSIZ`

     :type: ``C/int``

:var:`libc/EOF`

     :type: ``C/int``

:var:`libc/NULL`

     :type: ``C/pointer``

     .. note::

	Not an integer!

From :file:`stdint.h`:

:var:`libc/INTPTR_MIN`

     :type: ``libc/intptr_t``

:var:`libc/INTPTR_MAX`

     :type: ``libc/intptr_t``

:var:`libc/INTMAX_MIN`

     :type: ``libc/intmax_t``

:var:`libc/INTMAX_MAX`

     :type: ``libc/intmax_t``

:var:`libc/UINTMAX_MAX`

     :type: ``libc/uintmax_t``

From :file:`sys/resource.h`:

:var:`libc/RUSAGE_SELF`

     :type: ``C/int``

:var:`libc/RUSAGE_CHILDREN`

     :type: ``C/int``

.. note::

   ``RUSAGE_BOTH`` and ``RUSAGE_THREAD`` are not generic and not
   currently available.

:var:`libc/RLIM_SAVED_MAX`

     :type: ``libc/rlim_t``

     .. warning::

	Not all systems define ``RLIM_SAVED_MAX``.

:var:`libc/RLIM_SAVED_CUR`

     :type: ``libc/rlim_t``

     .. warning::

	Not all systems define ``RLIM_SAVED_CUR``.

:var:`libc/RLIM_INFINITY`

     :type: ``libc/rlim_t``

From :file:`sys/wait.h`:

:var:`libc/WAIT_ANY`

     :type: ``libc/pid_t``

:var:`libc/WNOHANG`

     :type: ``C/int``

:var:`libc/WUNTRACED`

     :type: ``C/int``

From :file:`termios.h`:

:var:`libc/TCSADRAIN`

     :type: ``C/int``

:var:`libc/TCSAFLUSH`

     :type: ``C/int``

From :file:`unistd.h`:

:var:`libc/PATH_MAX`

     :type: ``C/int``

:var:`libc/STDIN_FILENO`

     :type: ``C/int``

:var:`libc/STDOUT_FILENO`

     :type: ``C/int``

:var:`libc/STDERR_FILENO`

     :type: ``C/int``

:var:`libc/R_OK`

     :type: ``C/int``

:var:`libc/W_OK`

     :type: ``C/int``

:var:`libc/X_OK`

     :type: ``C/int``

:var:`libc/F_OK`

     :type: ``C/int``

.. _`libc/idio-uname`:

:var:`libc/idio-uname`

     :type: ``C/pointer`` to a ``struct utsname`` from :manpage:`uname(3)`

     .. code-block:: idio-console

	Idio> libc/idio-uname.sysname
	"Linux"

     Most of the elements are available as features to ``cond-expand``:

     .. code-block:: idio

	(cond-expand
	  (uname/sysname/SunOS ...)
	  (uname/sysname/FreeBSD ...)
	  (else ...))

.. _`libc/CLK_TCK`:

:var:`libc/CLK_TCK`

     :type: ``C/long``

     This is the value of ``sysconf (_SC_CLK_TCK)`` which is useful
     for normalising the results for :ref:`libc/times <libc/times>`.

OS-dependent libc Variables
===========================

Here the set of names in various groups, signals, error, etc., are
operating system-dependent.

Signal Names
------------

Surprisingly, despite using the macro value, say, ``SIGINT``, in
:lname:`C` code there is no way to get the descriptive string "SIGINT"
back out of the system.  :manpage:`strsignal(3)` provides the helpful
string "Interrupt".

We're following in the footsteps of :lname:`Bash`'s
:file:`support/signames.c`.

:var:`libc/SIGINT` :var:`libc/SIGTERM` ...

     These are operating system-dependent.

     For completeness a debug build will report on any signal numbers
     (between the lowest and highest defined) which do not have
     associated :lname:`C` definitions.  These will be added as
     :samp:`libc/SIGJUNK{nnn}`.

     The realtime signals, ``SIGRTMIN`` through to ``SIGRTMAX`` are
     not necessarily contiguous with regular signals.

You can convert a ``C/int`` signal number into either the short or
long form names (eg, ``INT`` or ``SIGINT``) with :ref:`libc/sig-name` and
:ref:`libc/signal-name`.

You can get a list of all signal numbers with short or long signal
names with :ref:`libc/sig-names` or :ref:`libc/signal-names`.

Error Names
-----------

:var:`libc/EACCESS` :var:`libc/EPERM` ...

     These are operating system-dependent.

     For completeness a debug build will report on any error numbers
     (between the lowest and highest defined) which do not have
     associated definitions.  These will be added as
     :samp:`libc/ERRUNKNOWN{nnn}`.

You can convert a ``C/int`` error number into the error name with
:ref:`libc/errno-name`.

You can get a list of all error numbers with error names with
:ref:`libc/errno-names`.

:ref:`libc/strerrno` is the moral equivalent of
:manpage:`strsignal(3)` and is functionally identical to
:ref:`libc/errno-name`.

:lname:`C`'s :ref:`errno <libc/errno>` is accessible as a computed variable.

RLIMIT Names
------------

:var:`libc/RLIMIT_NOFILE` ...

     These are operating system-dependent.

     For completeness a debug build will report on any ``RLIMIT``
     numbers (between the lowest and highest defined) which do not
     have associated definitions.  These will be added as
     :samp:`libc/RLIMIT_UNKNOWN{nnn}`.

You can convert a ``C/int`` RLIMIT number into the RLIMIT name with
:ref:`libc/rlimit-name`.

You can get a list of all RLIMIT numbers with names with
:ref:`libc/rlimit-names`.

Computed libc Variables
=======================

.. _`libc/errno`:

:var:`libc/errno`

     :type: ``C/int``

     .. note::

	There is no set method for this variable.

libc-api.c
==========

Rather than document the (continually updated)
:file:`.../ext/libc/src/libc-api.c` this documentation is tied to the
subset defined in :file:`src/build-bootstrap/libc-api.c`.

The contents are, being platform-specific, not especially generic,
however the intended portable interfaces are generic and we can
describe those.

System and Library Functions
----------------------------

The :val:`^rt-libc-format-error` is usually picking up on the attempt
to pass an :lname:`Idio` string with an embedded ASCII NUL into
:lname:`C`.

.. _`libc/access`:

.. function:: libc/access pathname mode

   Call :manpage:`access(2)`.

   :param pathname:
   :type pathname: string
   :param mode: :var:`R_OK` etc.
   :type mode: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error`
   :rtype: boolean

.. _`libc/chdir`:

.. function:: libc/chdir path

   Call :manpage:`chdir(2)`.

   :param path:
   :type path: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/close`:

.. function:: libc/close fd

   Call :manpage:`close(2)`.

   :param fd: file descriptor to close
   :type fd: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/dup`:

.. function:: libc/dup oldfd

   Call :manpage:`dup(2)`.

   :param oldfd: file descriptor to dup
   :type oldfd: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/dup2`:

.. function:: libc/dup2 oldfd newfd

   Call :manpage:`dup2(2)`.

   :param oldfd: file descriptor to dup
   :type oldfd: ``C/int``
   :param newfd: file descriptor to overwrite
   :type newfd: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/exit`:

.. function:: libc/exit status

   Call :manpage:`exit(3)`.

   :param status:
   :type status: fixnum or ``C/int``

   Obviously, ``exit`` does not return!

   The use of a fixnum here is a convenience for the likes of:

   .. code-block:: idio

      exit 1

.. _`libc/fcntl`:

.. function:: libc/fcntl fd cmd [arg]

   Call :manpage:`fcntl(2)`.

   :param fd: file descriptor
   :type fd: ``C/int``
   :param cmd: fcntl command
   :type cmd: ``C/int``
   :param arg: (optional) fcntl command argument
   :type arg: varies
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

   Supported commands include:
   
   * ``F_DUPFD``

     :param arg: file descriptor to duplicate
     :type arg: ``C/int``


   * ``F_DUPFD_CLOEXEC`` (if supported)

     :param arg: file descriptor to duplicate
     :type arg: ``C/int``

   * ``F_GETFD``

   * ``F_SETFD``

     :param arg: file descriptor flags
     :type arg: ``C/int``

   * ``F_GETFL``

   * ``F_SETFL``

     :param arg: file status flags
     :type arg: ``C/int``

     See :ref:`file status flags <libc/file status flags>` for what
     might be possible.

.. _`libc/fork`:

.. function:: libc/fork

   Call :manpage:`fork(2)`.

   :raises: :val:`^system-error`
   :rtype: ``libc/pid_t``

.. _`libc/getcwd`:

.. function:: libc/getcwd

   Call :manpage:`getcwd(3)`.

   :raises: :val:`^system-error`
   :rtype: string

.. _`libc/getpgpid`:

.. function:: libc/getpgpid

   Call :manpage:`getpgpid(2)`.

   :raises: :val:`^system-error`
   :rtype: ``libc/pid_t``

.. _`libc/getpgrp`:

.. function:: libc/getpgrp

   Call :manpage:`getpgrp(2)`.

   :raises: :val:`^system-error`
   :rtype: ``libc/pid_t``

.. _`libc/getpid`:

.. function:: libc/getpid

   Call :manpage:`getpid(2)`.

   :raises: :val:`^system-error`
   :rtype: ``libc/pid_t``

.. _`libc/getrlimit`:

.. function:: libc/getrlimit resource

   Call :manpage:`getrlimit(2)`.

   :param resource: ``libc/RLIMIT_NOFILE`` etc.
   :type resource: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/pointer`` to a :ref:`struct rlimit <libc/struct rlimit>`

.. _`libc/getrusage`:

.. function:: libc/getrusage who

   Call :manpage:`getrusage(2)`.

   :param who: ``libc/RUSAGE_SELF`` etc.
   :type who: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/pointer`` to a :ref:`struct rusage <libc/struct rusage>`

.. _`libc/getsid`:

.. function:: libc/getsid

   Call :manpage:`getsid(2)`.

   :raises: :val:`^system-error`
   :rtype: ``libc/pid_t``

.. _`libc/gettimeofday`:

.. function:: libc/gettimeofday

   Call :manpage:`gettimeofday(2)`.

   :raises: :val:`^system-error`
   :rtype: ``C/pointer`` to a :ref:`struct timeval <libc/struct timeval>`

.. _`libc/isatty`:

.. function:: libc/isatty

   Call :manpage:`isatty(3)`.

   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

   .. note::

      ``libc/isatty`` is strictly conforming to the library call model
      and raising a condition if the call fails.

      Use the :ref:`T? <T?>` shell predicate to get a boolean result.

.. _`libc/kill`:

.. function:: libc/kill pid sig

   Call :manpage:`kill(2)`.

   :param pid: process ID
   :type pid: ``libc/pid_t``
   :param sig: signal
   :type sig: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/mkdir`:

.. function:: libc/mkdir pathname mode

   Call :manpage:`mkdir(2)`.

   :param pathname:
   :type pathname: string
   :param mode:
   :type mode: ``libc/mode_t``
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :rtype: ``C/int``

   .. note::

      Few ``libc/mode_t`` values are defined.  The :ref:`libc/S_ISDIR
      <libc/S_ISDIR>` etc. macros are defined.

.. _`libc/mkdtemp`:

.. function:: libc/mkdtemp template

   Call :manpage:`mkdtemp(3)`.

   :param template:
   :type template: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :return: the unique directory name
   :rtype: string

.. _`libc/mkstemp`:

.. function:: libc/mkstemp template

   Call :manpage:`mkstemp(3)`.

   This is complicated by ``mkstemp`` also returning an open file
   descriptor to the unique temporary file.  In particular ``mkstemp``
   modifies the (:lname:`C`) template which the caller can review.
   Here we generate a new :lname:`Idio` string from the :lname:`C`
   version of :var:`template`.

   :param template:
   :type template: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :return: a list of the open file descriptor and the unique file name
   :rtype: list (``C/int`` string)

.. _`libc/pipe`:

.. function:: libc/pipe

   Call :manpage:`pipe(2)`.

   ``pipe`` takes an ``int[]`` which isn't an :lname:`Idio` accessible
   type so there are two ancillary functions, :ref:`pipe-reader
   <libc/pipe-reader>` and :ref:`pipe-writer <libc/pipe-writer>` which
   take the result of this call and return the individual elements.

   :raises: :val:`^system-error`
   :rtype: ``C/pointer``

.. _`libc/pipe-reader`:

.. function:: libc/pipe-reader v

   :param v: the result of calling :ref:`pipe <libc/pipe>`
   :type v: ``C/pointer``
   :rtype: ``C/int``

.. _`libc/pipe-writer`:

.. function:: libc/pipe-writer v

   :param v: the result of calling :ref:`pipe <libc/pipe>`
   :type v: ``C/pointer``
   :rtype: ``C/int``

.. _`libc/read`:

.. function:: libc/read fd [count]

   Call :manpage:`read(2)`.

   :param fd: the file descriptor to read from
   :type fd: ``C/int``
   :param count: (optional) the number of bytes to read
   :type count: fixnum or ``libc/size_t``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :return: a string of the bytes read or ``#<eof>``
   :rtype: string or ``#<eof>``

   The use of a fixnum here is because you're unlikely to have the
   appropriate ``libc/size_t`` as the result of a previous operation
   other than, possibly, using :ref:`libc/BUFSIZ <libc/BUFSIZ>`.  So,
   on the rare occasion you need to supply a count, a fixnum is
   convenient.

.. _`libc/rmdir`:

.. function:: libc/rmdir pathname

   Call :manpage:`rmdir(2)`.

   :param pathname:
   :type pathname: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/setpgpid`:

.. function:: libc/setpgpid pid pgid

   Call :manpage:`setpgpid(2)`.

   :param pid: process ID to affect
   :type pid: ``C/int``
   :param pgid: process group ID
   :type pgid: ``C/int``
   :raises: :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/setrlimit`:

.. function:: libc/setrlimit resource rlim

   Call :manpage:`setrlimit(2)`.

   ``rlim`` should be the (modified) value returned from
   :ref:`libc/getrlimit <libc/getrlimit>`.

   :param resource: ``libc/RLIMIT_NOFILE`` etc.
   :type resource: ``C/int``
   :param rlim: resource limit
   :type rlim: ``C/pointer`` to a :ref:`struct rlimit <libc/struct rlimit>`
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error` :val:`^system-error`
   :rtype: ``#<unspec>``

   By way of example, this code from :file:`lib/test.idio` actively
   limits the number of open file descriptors to 256:

   .. code-block:: idio

      nofiles_lim := 256
      C_nofiles_lim := C/integer-> nofiles_lim libc/rlim_t
      rl := libc/getrlimit libc/RLIMIT_NOFILE
      if (C/> rl.rlim_cur C_nofiles_lim) {
	rl.rlim_cur = C_nofiles_lim
	libc/setrlimit libc/RLIMIT_NOFILE rl
      }

   Notice that we have to convert our 256 into the correct :lname:`C`
   base type.

.. _`libc/signal`:

.. function:: libc/signal sig handler

   Call :manpage:`signal(2)`.

   :param sig: signal
   :type sig: ``C/int``
   :param handler: signal disposition
   :type handler: ``C/pointer``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :return: previous disposition
   :rtype: ``C/pointer``

   :var:`libc/SIG_DFL` and :var:`libc/SIG_IGN` are defined for use as
   ``handler``, here.

.. _`libc/sleep`:

.. function:: libc/sleep seconds

   Call :manpage:`sleep(3)`.

   :param seconds: seconds to sleep
   :type seconds: fixnum or ``C/uint``
   :raises: :val:`^rt-parameter-type-error`
   :return: the number of seconds remaining if interrupted
   :rtype: ``C/uint``

   A fixnum, here, is very convenient.

.. _`libc/stat`:

.. function:: libc/stat pathname

   Call :manpage:`stat(2)`.

   :param pathname: pathname to stat
   :type pathname: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :return: the struct stat
   :rtype: ``C/pointer`` to a :ref:`libc/struct stat <libc/struct stat>`

.. _`libc/S_ISBLK`:

.. function:: libc/S_ISBLK mode

   Call the :lname:`C` macro ``S_ISBLK``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISCHR`:

.. function:: libc/S_ISCHR mode

   Call the :lname:`C` macro ``S_ISCHR``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISDIR`:

.. function:: libc/S_ISDIR mode

   Call the :lname:`C` macro ``S_ISDIR``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISREG`:

.. function:: libc/S_ISREG mode

   Call the :lname:`C` macro ``S_ISREG``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISLNK`:

.. function:: libc/S_ISLNK mode

   Call the :lname:`C` macro ``S_ISLNK``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISFIFO`:

.. function:: libc/S_ISFIFO mode

   Call the :lname:`C` macro ``S_ISFIFO``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/S_ISSOCK`:

.. function:: libc/S_ISSOCK mode

   Call the :lname:`C` macro ``S_ISSOCK``.

   :param mode: mode to test
   :type mode: ``libc/mode_t``
   :rtype: boolean

.. _`libc/strerror`:

.. function:: libc/strerror errnum

   Call :manpage:`strerror(3)`.

   :param errnum: errnum to decode
   :type errnum: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :return: the error message
   :rtype: string

.. _`libc/strsignal`:

.. function:: libc/strsignal sig

   Call :manpage:`strsignal(3)`.

   :param sig: the signal number to decode
   :type sig: ``C/int``
   :raises: :val:`^rt-parameter-type-error`
   :return: the strsignal buf
   :rtype: string (see note)

   .. note::

      On some systems, SunOS, :manpage:`strsignal(3)` will return
      NULL, eg. for -1.  Here we return ``#n``.

.. _`libc/tcgetattr`:

.. function:: libc/tcgetattr fd

   Call :manpage:`tcgetattr(3)`.

   :param fd: the file descriptor
   :type fd: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :var:`^system-error`
   :return: the termios structure
   :rtype: ``C/pointer`` to a :ref:`libc/struct termios <libc/struct termios>`

.. _`libc/tcgetpgrp`:

.. function:: libc/tcgetpgrp fd

   Call :manpage:`tcgetpgrp(3)`.

   :param fd: the file descriptor
   :type fd: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :var:`^system-error`
   :return: process ID
   :rtype: ``libc/pid_t``

.. _`libc/tcsetattr`:

.. function:: libc/tcsetattr fd options termios

   Call :manpage:`tcsetattr(3)`.

   :param fd: the file descriptor
   :type fd: ``C/int``
   :param options: options
   :type options: ``C/int``
   :param termios: the termios structure
   :type termios: ``C/pointer`` to a :ref:`libc/struct termios <libc/struct termios>`
   :raises: :val:`^rt-parameter-type-error` :var:`^system-error`
   :return: the termios structure
   :rtype: ``C/pointer`` to a :ref:`libc/struct termios <libc/struct termios>`

   The following options are defined: :var:`libc/TCSADRAIN` and
   :var:`libc/TCSAFLUSH`.

   See :ref:`libc/tcgetattr <libc/tcgetattr>` for obtaining a ``struct
   termios``.

.. _`libc/tcsetpgrp`:

.. function:: libc/tcsetpgrp fd pgrp

   Call :manpage:`tcsetpgrp(3)`.

   :param fd: the file descriptor
   :type fd: ``C/int``
   :param pgrp: the process group ID
   :type pgrp: ``libc/pid_t``
   :raises: :val:`^rt-parameter-type-error` :var:`^system-error`
   :rtype: ``C/int``

.. _`libc/times`:

.. function:: libc/times

   Call :manpage:`times(3)`.

   :raises: :var:`^system-error`
   :rtype: list of (``libc/clock_t`` ``C/pointer`` to a :ref:`libc/struct tms <libc/struct tms>`)

   See also :ref:`libc/CLK_TCK <libc/CLK_TCK>`.

.. _`libc/uname`:

.. function:: libc/uname

   Call :manpage:`uname(3)`.

   :raises: :var:`^system-error`
   :rtype: ``C/pointer`` to a :ref:`libc/struct utsname <libc/struct utsname>`

   See also :ref:`libc/idio-uname <libc/idio-uname>` which has already
   called this function.

.. _`libc/unlink`:

.. function:: libc/unlink pathname

   Call :manpage:`unlink(2)`.

   :param pathname:
   :type pathname: string
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-libc-format-error` :val:`^system-error`
   :rtype: ``C/int``

.. _`libc/waitpid`:

.. function:: libc/waitpid pid options

   Call :manpage:`waitpid(2)`.

   :param pid: process ID
   :type pid: ``libc/pid_t``
   :param options: 
   :type options: ``C/int``
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :return: the process and status
   :rtype: list of (``libc/pid_t`` ``C/pointer``)

   :var:`libc/WAIT_ANY` is defined as -1 in place of ``pid``.

   The following options are defined: :var:`libc/WNOHANG`
   :var:`libc/WUNTRACED`.

   The returned ``C/pointer`` is a :lname:`C` ``int *``.  See
   :ref:`libc/WIFEXITED <libc/WIFEXITED>`, :ref:`libc/WEXITSTATUS
   <libc/WEXITSTATUS>`, :ref:`libc/WIFSIGNALLED <libc/WIFSIGNALLED>`,
   :ref:`libc/WTERMSIG <libc/WTERMSIG>`, :ref:`libc/WIFSTOPPED
   <libc/WIFSTOPPED>` for functions to manipulate this value.

.. _`libc/WIFEXITED`:

.. function:: libc/WIFEXITED status

   Call the :lname:`C` macro ``WIFEXITED``.

   :param status: status
   :type status: ``C/pointer``
   :rtype: boolean

.. _`libc/WEXITSTATUS`:

.. function:: libc/WEXITSTATUS status

   Call the :lname:`C` macro ``WEXITSTATUS``.

   :param status: status
   :type status: ``C/pointer``
   :rtype: ``C/int``

.. _`libc/WIFSIGNALLED`:

.. function:: libc/WIFSIGNALLED status

   Call the :lname:`C` macro ``WIFSIGNALLED``.

   :param status: status
   :type status: ``C/pointer``
   :rtype: boolean

.. _`libc/WTERMSIG`:

.. function:: libc/WTERMSIG status

   Call the :lname:`C` macro ``WTERMSIG``.

   :param status: status
   :type status: ``C/pointer``
   :rtype: ``C/int``

.. _`libc/WIFSTOPPED`:

.. function:: libc/WIFSTOPPED status

   Call the :lname:`C` macro ``WIFSTOPPED``.

   :param status: status
   :type status: ``C/pointer``
   :rtype: boolean

.. _`libc/write`:

.. function:: libc/write fd str

   Call :manpage:`write(2)`.

   :param fd: the file descriptor to write to
   :type fd: ``C/int``
   :param str: the string to write
   :type str: string
   :raises: :val:`^rt-parameter-type-error` :val:`^system-error`
   :return: the number of bytes written
   :rtype: ``libc/ssize_t``

.. _`libc/file status flags`:

File Status Flags
^^^^^^^^^^^^^^^^^

File status flags are a bit inconsistent across platforms so the
results may not be portable.  But you knew that anyway, right?

File *access modes* are available on all platforms:

:var:`O_RDONLY`

:var:`O_WRONLY`

:var:`O_RDWR`

Linux notes a distinction between file *creation* flags (the first few
in the table below) and further file *status* flags in addition to the
creation flags.

I'm working on the basis that the manual pages speak the intent of the
platform even if the header files are a little more generous.
Ostensibly, Mac OS, for example, doesn't use any of the *SYNC* flags
yet they are defined in the header files.

Together with flags from other systems we have the following table:

.. csv-table::
   :header: "flag", "Linux", "FreeBSD", "SunOS", "Mac OS", "notes"
   :align: left
   :widths: auto

   
   :var:`O_CLOEXEC`, Y, Y, Y, Y, *creation*
   :var:`O_CREAT`, Y, Y, Y, Y, *creation*
   :var:`O_DIRECTORY`, Y, Y, \-, \-, *creation*
   :var:`O_EXCL`, Y, Y, Y, Y, *creation*
   :var:`O_NOCTTY`, Y, i, Y, \-, *creation*
   :var:`O_NOFOLLOW`, Y, Y, Y, Y, *creation*
   :var:`O_TRUNC`, Y, Y, Y, Y, *creation*

   :var:`O_APPEND`, Y, Y, Y, Y
   :var:`O_ASYNC`, Y, \-, Y, \-
   :var:`O_DIRECT`, Y, Y, Y, \-
   :var:`O_DSYNC`, Y, Y, Y, \-
   :var:`O_FSYNC`, Y, Y, \-, Y, synonym for :var:`O_SYNC`
   :var:`O_EXLOCK`, \-, Y, \-, Y
   :var:`O_LARGEFILE`, Y, \-, Y, \-
   :var:`O_NONBLOCK`, Y, Y, Y, Y
   :var:`O_NDELAY`, Y, Y, Y, Y, synonym for :var:`O_NONBLOCK`
   :var:`O_PATH`, Y, \-, \-, \-
   :var:`O_SHLOCK`, \-, Y, \-, Y
   :var:`O_SYNC`, Y, Y, Y, \-

i -- is ignored on FreeBSD

(I've ignored flags which appear to be unique to a platform.)

So, pretty spotty.  Once a file is open, most flags are ignored when
you come to (try to) change then with :manpage:`fnctl(2)`.  Linux
notes:

    File access mode (O_RDONLY, O_WRONLY, O_RDWR) and file creation
    flags (i.e., O_CREAT, O_EXCL, O_NOCTTY, O_TRUNC) in arg are
    ignored.  On Linux, this command can change only the O_APPEND,
    O_ASYNC, O_DIRECT, O_NOATIME, and O_NONBLOCK flags.

Other systems have varying support as well.

I guess, like error numbers, signal numbers etc., we expose what the
platform exposes.

POSIX regex
-----------

The POSIX :manpage:`regex(3)` functions are defined in
:file:`src/posix-regex.c` and the primitives are available to all
which, together with the routines in :file:`lib/posix-regex.idio`,
give rise to the fundamental to pattern matching in :lname:`Idio`.

.. _`libc/regcomp`:

.. function:: libc/regcomp rx [flags]

   Call :manpage:`regcomp(3)`.

   Of course the user can't pass in a ``regex_t *`` so this code will
   create one and return it.

   :param rx: the regular expression
   :type rx: string
   :param flags: (optional) flags
   :type flags: symbols
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error` :val:`^rt-regex-error`
   :return: the compiled regular expression
   :rtype: ``C/pointer``

   The ``flags`` are: :var:`REG_EXTENDED`, :var:`REG_ICASE`,
   :var:`REG_NOSUB` (ignored) and :var:`REG_NEWLINE`.

   Like other systems, this code defaults to :var:`REG_EXTENDED` so
   there is an extra :var:`REG_BASIC` flag to disable
   :var:`REG_EXTENDED`.

.. _`libc/regexec`:

.. function:: libc/regexec rx str [flags]

   Call :manpage:`regexec(3)`.

   Of course the user can't pass in a ``regex_t *`` so this code will
   create one and return it.

   :param rx: the compiled regular expression
   :type rx: ``C/pointer``
   :param str: the string to match against
   :type str: string
   :param flags: (optional) flags
   :type flags: symbols
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :return: an array of matching subexpressions or ``#f`` if no match

   The ``flags`` are: :var:`REG_NOTBOL`, :var:`REG_NOTEOL` and
   :var:`REG_STARTEND`(if supported).

   On a successful match an array of the subexpressions in ``rx`` is
   returned with the first (zero-th) being the entire matched string.

   If a subexpression in ``rx`` matched the corresponding array
   element will be the matched string.

   If a subexpression in ``rx`` did not match the corresponding array
   element will be ``#f``.

The POSIX functions :manpage:`regerror(3)` and :manpage:`regfree(3)`
are automatically invoked where required.

:file:`lib/posix-regex.idio` defines two shell-like pattern matching
functions (technically, templates).

.. _`regex-case`:

.. function:: regex-case str *clauses*

   ``regex-case`` works like ``case`` in that it takes a sequence of
   clauses where the first element of each clause is a regular
   expression to be compared to ``str`` in turn.

   If a regular expression matches then the clauses remaining
   expressions are run and the final value is the value ``regex-case``
   returns.

   An ``else`` clause is permitted.

   The array returned from ``regexec`` is available in the remaining
   expressions as the variable :var:`r`.

   The code is complicated slightly by endeavouring to remember the
   (otherwise) interim compiled regular expressions in case this
   expression is run in a loop.

   .. code-block:: idio

      (regex-case libc/idio-uname.release
        ("^([[:digit:]]\\.[[:digit:]]+)" {
	   printf "this is a %s kernel\n" r.1		; this is a 5.11 kernel
	 }))

``regex-case`` is too visually complex for most of the *pattern
matching* that I do, usually with :lname:`Bash`'s ``case`` statement.
For those circumstances we can put a wrapper around ``regex-case`` and
further use ``regex-case`` to pick out ``*`` and ``?`` and replace
them with ``.*`` and ``.`` respectively giving us:

.. _`pattern-case`:

.. function:: pattern-case str *clauses*

   .. code-block:: idio

      (pattern-case libc/idio-uname.sysname
        ("SunOS" {
	   printf "this is Solaris\n"
	 })
        ("*BSD" {
	   printf "this is a BSD\n"
	 })
	(else {
	   printf "this isn't Solaris\n"
	 }))



Structures and Accessors
------------------------

.. _`libc/struct rlimit`:

:val:`libc/struct rlimit`

     .. attribute:: rlim_cur

	:type: ``libc/rlim_t``

     .. attribute:: rlim_max

	:type: ``libc/rlim_t``

.. _`libc/struct-rlimit-ref`:

.. function:: libc/struct-rlimit-ref rlimit member

   :param rlimit:
   :type rlimit: ``C/pointer`` to a ``struct rlimit``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: ``libc/rlim_t``

.. _`libc/struct-rlimit-set!`:

.. function:: libc/struct-rlimit-set! rlimit member val

   :param rlimit:
   :type rlimit: ``C/pointer`` to a ``struct rlimit``
   :param member: structure member name
   :type member: symbol
   :param val: 
   :type val: ``libc/rlim_t``
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: ``#<unspec>``

.. _`libc/struct rusage`:

:val:`libc/struct rusage`

     .. attribute:: ru_utime

	:type: ``C/pointer`` to a :ref:`struct timeval <libc/struct timeval>`

     .. attribute:: ru_stime

	:type: ``C/pointer`` to a :ref:`struct timeval <libc/struct timeval>`

     .. note::

	Other members are not available yet -- and are operating
	system-dependent.

.. _`libc/struct-rusage-ref`:

.. function:: libc/struct-rusage-ref rusage member

   :param rusage:
   :type rusage: ``C/pointer`` to a ``struct rusage``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. note::

   There is no ``libc/struct-rusage-set!`` function.

.. _`libc/struct stat`:

:val:`libc/struct stat`

     Most of the fields are as you would expect except modern
     timestamps are different.

     .. attribute:: st_dev

	:type: ``libc/dev_t``

     .. attribute:: st_ino

	:type: ``libc/ino_t``

     .. attribute:: st_nlink

	:type: ``libc/nlink_t``

     .. attribute:: st_mode

	:type: ``libc/mode_t``

     .. attribute:: st_uid

	:type: ``libc/uid_t``

     .. attribute:: st_gid

	:type: ``libc/gid_t``

     .. attribute:: st_rdev

	:type: ``libc/dev_t``

     .. attribute:: st_size

	:type: ``libc/off_t``

     .. attribute:: st_blksize

	:type: ``libc/blksize_t``

     .. attribute:: st_blocks

	:type: ``libc/blkcnt_t``

     In the before-times, a Unix filesystem timestamp was a ``time_t``
     but these have all been migrated to ``struct timespec``.  The
     rather useful side-effect of using a ``struct timespec`` is that
     the ``tv_sec`` member is a ``time_t`` (and now a 64-bit value) so
     by some judicious ``#define``\ s they could maintain the illusion
     of the traditional interface whilst allowing progressive code to
     access the finer-grained value.

     ``#define``\ s aren't visible to the code-generating system so
     these old-ways have been manually added.

     There's another slight complication in that most operating
     systems call the new ``struct timepsec`` field, say, ``st_atim``
     -- without the trailing ``e``.  However, Mac OS calls the fields
     an, arguably better, ``st_atimespec``.

     I've normalised to ``st_atim`` on all systems for better or for
     worse.

     .. attribute:: st_atim

	:type: ``C/pointer`` to a :ref:`libc/struct timespec <libc/struct timespec>`

     .. attribute:: st_atime

	:type: ``libc/time_t``

     .. attribute:: st_mtim

	:type: ``C/pointer`` to a :ref:`libc/struct timespec <libc/struct timespec>`

     .. attribute:: st_mtime

	:type: ``libc/time_t``

     .. attribute:: st_ctim

	:type: ``C/pointer`` to a :ref:`libc/struct timespec <libc/struct timespec>`

     .. attribute:: st_ctime

	:type: ``libc/time_t``

     .. note::

	Other members are not available yet -- and are operating
	system-dependent.

.. _`libc/struct-stat-ref`:

.. function:: libc/struct-stat-ref stat member

   :param stat:
   :type stat: ``C/pointer`` to a ``struct stat``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. note::

   There is no ``libc/struct-stat-set!`` function.

.. _`libc/struct termios`:

:val:`libc/struct termios`

     .. attribute:: c_iflag

	:type: ``libc/tcflag_t``

     .. attribute:: c_oflag

	:type: ``libc/tcflag_t``

     .. attribute:: c_cflag

	:type: ``libc/tcflag_t``

     .. attribute:: c_lflag

	:type: ``libc/tcflag_t``

     .. attribute:: c_cc

	:type: ``libc/cc_t *``

	Technically, the type is ``cc_t[]``.


     The following members are non-portable and cannot be referenced
     or set at the moment.

     .. attribute:: c_line

	:type: ``libc/cc_t``

	Linux only.

     .. attribute:: c_ispeed

	:type: ``libc/speed_t``

	Not in SunOS.

     .. attribute:: c_ospeed

	:type: ``libc/speed_t``

	Not in SunOS.

.. _`libc/struct-termios-ref`:

.. function:: libc/struct-termios-ref termios member

   :param termios:
   :type termios: ``C/pointer`` to a ``struct termios``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. _`libc/struct-termios-set!`:

.. function:: libc/struct-termios-set! termios member val

   :param termios:
   :type termios: ``C/pointer`` to a ``struct termios``
   :param member: structure member name
   :type member: symbol
   :param val: 
   :type val: as appropriate
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: ``#<unspec>``

.. _`libc/struct timespec`:

:val:`libc/struct timespec`

     .. attribute:: tv_sec
	:noindex:

	:type: ``libc/time_t``

     .. attribute:: tv_nsec

	:type: ``C/long``

	.. note::

	   Some systems define ``tv_nsec`` as a ``__syscall_slong_t``
	   which appears to be a ``long``.

.. _`libc/struct-timespec-ref`:

.. function:: libc/struct-timespec-ref timespec member

   :param timespec:
   :type timespec: ``C/pointer`` to a ``struct timespec``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. _`libc/struct-timespec-set!`:

.. function:: libc/struct-timespec-set! timespec member val

   :param timespec:
   :type timespec: ``C/pointer`` to a ``struct timespec``
   :param member: structure member name
   :type member: symbol
   :param val: 
   :type val: ``libc/time_t`` or ``libc/suseconds_t`` as appropriate
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: ``#<unspec>``

.. _`libc/struct timeval`:

:val:`libc/struct timeval`

     .. attribute:: tv_sec

	:type: ``libc/time_t``

     .. attribute:: tv_usec

	:type: ``libc/suseconds_t``

	.. note::

	   Not all systems define a ``suseconds_t`` so
	   :file:`ext/libc/src/lib-api.c` typedefs either
	   ``__suseconds_t`` or ``long``.

.. _`libc/struct-timeval-ref`:

.. function:: libc/struct-timeval-ref timeval member

   :param timeval:
   :type timeval: ``C/pointer`` to a ``struct timeval``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. _`libc/struct-timeval-set!`:

.. function:: libc/struct-timeval-set! timeval member val

   :param timeval:
   :type timeval: ``C/pointer`` to a ``struct timeval``
   :param member: structure member name
   :type member: symbol
   :param val: 
   :type val: ``libc/time_t`` or ``libc/suseconds_t`` as appropriate
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: ``#<unspec>``

.. function:: libc/add-struct-timeval tv1 tv2

   :param tv1:
   :type tv1: ``C/pointer`` to a ``struct timeval``
   :param tv2:
   :type tv2: ``C/pointer`` to a ``struct timeval``
   :rtype: ``C/pointer`` to a :ref:`struct timeval <libc/struct timeval>`

.. function:: libc/subtract-struct-timeval tv1 tv2

   :param tv1:
   :type tv1: ``C/pointer`` to a ``struct timeval``
   :param tv2:
   :type tv2: ``C/pointer`` to a ``struct timeval``
   :rtype: ``C/pointer`` to a :ref:`struct timeval <libc/struct timeval>`

.. _`libc/struct-timeval-as-string`:

.. function:: libc/struct-timeval-as-string timeval

   :param timeval:
   :type timeval: ``C/pointer`` to a ``struct timeval``
   :raises: :val:`^rt-parameter-value-error`
   :rtype: string

   Returns the common ``%ld.%06ld`` format -- where the precision,
   ``6``, may be overridden by :ref:`%format <%format>`.

.. _`libc/struct tms`:

:val:`libc/struct tms`

     .. attribute:: tms_utime

	:type: ``libc/clock_t``

     .. attribute:: tms_stime

	:type: ``libc/clock_t``

     .. attribute:: tms_cutime

	:type: ``libc/clock_t``

     .. attribute:: tms_cstime

	:type: ``libc/clock_t``

     .. note::

	Other members are not available yet -- and are operating
	system-dependent.

.. _`libc/struct-tms-ref`:

.. function:: libc/struct-tms-ref tms member

   :param tms:
   :type tms: ``C/pointer`` to a ``struct tms``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. note::

   There is no ``libc/struct-tms-set!`` function.

.. _`libc/struct utsname`:

:val:`libc/struct utsname`

     .. attribute:: sysname

	:type: string

     .. attribute:: nodename

	:type: string

     .. attribute:: release

	:type: string

     .. attribute:: version

	:type: string

     .. attribute:: machine

	:type: string

     .. note::

	Other members are not available yet -- and are operating
	system-dependent.

.. _`libc/struct-utsname-ref`:

.. function:: libc/struct-utsname-ref utsname member

   :param utsname:
   :type utsname: ``C/pointer`` to a ``struct utsname``
   :param member: structure member name
   :type member: symbol
   :raises: :val:`^rt-parameter-type-error` :val:`^rt-parameter-value-error`
   :rtype: member-specific

.. note::

   There is no ``libc/struct-utsname-set!`` function.


.. include:: ../../commit.rst


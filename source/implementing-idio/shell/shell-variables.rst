.. include:: ../../global.rst

.. _`shell variables`:

***************
Shell Variables
***************

We need some shell variables, environment variables, etc. set up when
we start.  For some of these, notably, environment variables, we
should be good to go as we pick up on, *duh*, the values in our
environment noting there are possibly some that we *require*.  We
can't assume there is a :envvar:`PATH`, for example.

Just out of interest let's give :program:`bash` an empty environment
and then get it to print out its (created) environment:

.. code-block:: console

   $ env - bash -c env
   PWD=/home/idf
   SHLVL=0
   _=/usr/bin/env

Hmm, less than I thought.  Not *even* an exported :envvar:`PATH`.
*Interesting.* Of course, if we print out the shell variables with
``set``, it's something more expected:

.. code-block:: console

   $ env - bash -c set
   BASH=/usr/bin/bash
   ...
   IFS=$' \t\n'
   PATH=/usr/local/bin:/usr/bin
   PWD=/home/idf
   SHELL=/bin/bash
   ...

Hmm, what are the semantics of process behaviour, here, with regard to
environment variables?  Should we intervene or be invisible?

Another consideration is *how* we choose to intervene.  We have a
model which uses distinct *dynamic* and *environ* variables.  Can we
switch between the two?  (Currently, no!)

.. rst-class:: center

\*

There's also a subtlety regarding whether arguments are for us,
:lname:`Idio`, or the script we are intending to run.

Problems, problems!

main
====

In :lname:`C`, of course, we are given ``argc`` and ``argv``.  We're
going to follow in the style of :lname:`Bash` and propose:

.. parsed-literal::

   .../idio [*Idio-args*] [*script-name* [*script-args*]]

where arguments to :lname:`Idio` must come before any script name or
arguments to the script as, both in essence and in practice, the first
argument that isn't recognised as an :lname:`Idio` argument will be
treated as the name of a script.  ``--hlep`` beware!

Another, slightly less obvious, issue is that there is no mechanism to
load multiple libraries/scripts in one as I had been doing until
"normalizing" argument handling.  ``.../idio test test`` would run the
test suite twice.

Of course, this merely forces us to implement a :samp:`--load {name}`
argument so nothing ostensibly difficult there.  Except we need to be
cautious about handling any errors.

Variables
=========

What variables, in addition to a potential :envvar:`IDIOLIB` (see
:ref:`where are we`), should we be looking at creating?  There's
potential complications here between "shell" and environment variables
and what `POSIX thinks of them
<https://pubs.opengroup.org/onlinepubs/9699919799/>`_.

Here, we're don't particular feel bound by POSIX but we do want to be
good neighbours.  *We* might be able to handle environment variable
names with "non-portable" characters in them, notably hyphens -,
U+002D (HYPHEN-MINUS), but other users of the environment might not.

POSIX's list of "avoid conflict with" environment variables is
somewhat dubious appearing to be someone typing ``env | sort`` and
dumping it in the specification.  :envvar:`RANDOM` and
:envvar:`SECONDS` are *environment* variables?

.. rst-class:: center

\*

From our declaration of argument handling we should be able to derive:

:var:`SHELL`

     (environment variable)

     I originally had this down as the full pathname of ``.../idio``
     however POSIX thinks of it as the user's preferred command
     interpreter

     :lname:`Bash` says:

	    expands to the full pathname to the shell.  If it is not
	    set when the shell starts, bash assigns to it the full
	    pathname of the current user's login shell.

     Do as :lname:`Bash` does!

:var:`IDIO_CMD`

     (shell variable)

     This is ``argv[0]`` as :lname:`Idio` sees it.  It probably isn't
     useful but maybe someone wants to know how the command was
     invoked.

:var:`IDIO_EXE`

     (shell variable)

     This is the kernel or ``argv[0]`` derived full pathname of the
     running executable.

     I see :lname:`Bash` has both:

     - :var:`_` being variously the "pathname used to invoke the shell
       or shell script being executed" -- before becoming other things

     - :var:`BASH` being "the full filename used to invoke this
       instance of bash"

.. aside::

   Not only would a variable named :var:`0` be tricky to distinguish
   from the number 0 but we'd start heading down the route of that old
   FORTRAN trick where you could swap the numbers 2 and 3, say, with
   hilarious results.

   We don't use sigils in :lname:`Idio` and we can't have a variable
   called :var:`0` which leaves us with :var:`ARGV0`.

:var:`ARGV0`

     (shell variable)

     This is either the name of the running script or is identical to
     :var:`IDIO_CMD`.

     This is more similar to :lname:`Bash`'s :var:`$0` (and
     :var:`BASH_ARGV0`) which is the name of the shell script or shell
     if running interactively.

:var:`ARGC`

     (shell variable)

     This is the number of arguments to the *script*.

     Clearly, if no arguments are passed to the script then
     :var:`ARGC` is 0.  What if no script is being run, ie. we are in
     an interactive shell?  Arguably, :var:`ARGC` should be 0 again
     but currently it is -1 to distinguish that case.

:var:`ARGV`

     (shell variable)

     This is the arguments to the *script*.

:var:`IDIOLIB`

     (environment variable)

     calculated as described above

.. rst-class:: center

\*

Other values can be calculated and some are computed.

.. note::

   Most of the following are actually defined in
   :file:`src/libc-wrap.c` as they interact with the :lname:`C`
   standard library.

:var:`GROUPS`

     (shell variable)

     :type: array of ``libc/gid_t``

     An array of the current user's supplementary group IDs as given
     by :manpage:`getgroups(2)`.

:var:`HOME`

     (environment variable)

     the current user's home directory

:var:`HOSTNAME`

     (shell variable)

     the ``nodename`` field of a ``struct utsname`` from :manpage:`uname(3)`

     See also :ref:`libc/idio-uname <libc/idio-uname>`.

.. _IDIO_PID:

:var:`IDIO_PID`

     (shell variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getpid(2)`

     This value is not updated, see :ref:`PID <PID>`.

.. _IFS:

:var:`IFS`

     (dynamic variable)

     .. aside::

	I'll probably still call it Input Field Separator, though!

     I've always called this the *Input* Field Separator, after
     :program:`awk`, but I see I am completely wrong.  :program:`awk`
     never(?) had an :var:`IFS` but only an :var:`FS` which was "blank
     and tab" but separately has :var:`RS` the (input) *Record
     Separator* which is the newline you expect.

     :lname:`Bash` merged :var:`FS` and :var:`RS` into :var:`IFS`
     (*Internal* Field Separator) partly, I suppose, as it meant a
     single value would be used to split the entire multi-line output
     from *Command Substitution* whereas :program:`awk` would be
     expecting to (generally) process line by line.

     :program:`awk` does have distinct :var:`OFS` and :var:`ORS` when
     outputting whereas :lname:`Bash` uses the first character of
     :var:`IFS` in various expansion rules.

     There's no such output mangling in :lname:`Idio` -- we'd need to
     figure out something similar to :ref:`interpolated strings` -- so
     we'll hold off there.

     In the meanwhile, we can use the standard SPACE TAB NEWLINE for
     :var:`IFS`.

     Notice :var:`IFS` is a dynamic variable meaning you can redefine
     it for the duration of a block (rather than redefine it for
     everyone globally).

.. _PID:

:var:`PID`

     (shell variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getpid(2)`

     This value is updated when :lname:`Idio` forks.  Compare with
     :ref:`IDIO_PID <IDIO_PID>`.

:var:`PPID`

     (shell variable; POSIX says environment variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getppid(2)`

     This value is updated when :lname:`Idio` forks.

:var:`PWD`

     (environment variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getppid(2)`

Computed Variables
------------------

:var:`UID`

     (shell variable)

     :type: ``libc/uid_t``

     * accessing calls :manpage:`getuid(2)`

     * setting calls :manpage:`setuid(2)`

:var:`EUID`

     (shell variable)

     :type: ``libc/uid_t``

     * accessing calls :manpage:`geteuid(2)`

     * setting calls :manpage:`seteuid(2)`

:var:`GID`

     (shell variable)

     :type: ``libc/gid_t``

     * accessing calls :manpage:`getgid(2)`

     * setting calls :manpage:`setgid(2)`

:var:`EGID`

     (shell variable)

     :type: ``libc/gid_t``

     * accessing calls :manpage:`getegid(2)`

     * setting calls :manpage:`setegid(2)`


:var:`SECONDS`

     (shell variable)

     :type: integer

     The number of seconds since the VM was started.

     .. note::

	There is no set method for this variable.

.. include:: ../../commit.rst


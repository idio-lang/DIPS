.. include:: ../../global.rst

.. _`shell variables`:

***************
Shell Variables
***************

We need some shell variables, environment variables, etc. set up when
we start.  For some of these, notably, environment variables, we
should be good to go as we pick up on, *duh*, the values in our
environment noting there are some that we *require*.  We can't assume
there is a :envvar:`PATH`, for example.

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

Where Are We?
-------------

I often install bundles where you want to pick up items related to the
executable being run.  If you know this executable is
``.../bin/idio``, say, then you can find the libraries that *this*
executable was meant to run with in :file:`.../lib`.  This gives your
bundle the air of *position independence* which is extremely useful if
you have multiple, potentially incompatible, versions lying around.
Even better when you can :program:`tar` the bundle up and drop it
elsewhere and have it just work.

This sort of position independence is similar to the
:lname:`Python`-style *virtualenv* and RedHat *Software Collections*
both of which require that you explicitly run a command to "activate"
the new environment.  I've always worked with the idea that running a
command should be enough to activate the environment on its own.

That brings up a bit of a dance around auto-updating environment
variables which is influenced by whether or not environment variables
have been set at all.

* if :envvar:`IDIOLIB` is *unset* in the environment then we'll add
  the operating system-dependent standard library path to
  :envvar:`IDIOLIB`

* if the user has been wise and sensible enough to set :envvar:`PATH`
  to a bundle of :lname:`Idio` *in a non-standard location* then they
  are presumed to have been wise and sensible enough to have set
  :envvar:`IDIOLIB` to the right value

* however, if the executable was run with an explicit pathname
  (something with a ``/`` in it either absolute or relative) then we
  can take the liberty of *prepending* the executable-specific library
  files directory onto any extant :envvar:`IDIOLIB` setting

So, if the user hasn't set :envvar:`IDIOLIB` then they expect us to
figure out a sensible value which is either going to be the
executable-specific library files and/or the standard location
(operating system-dependent).

If the user has set :envvar:`IDIOLIB` we leave it alone.

Figuring out the pathname of the currently running executable is a
non-trivial exercise with plenty of operating system-bespoke special
cases and with the potential for no useful result whatsoever.

argv[0]
^^^^^^^

.. sidebox::

   ``argv[0]`` has its own issues.  We'll discuss these in a moment.

Most of the commands you run will be found on the :envvar:`PATH` and
will be launched (with :manpage:`execve(2)` or some-such) such that
``argv[0]`` is what you type, say, ``ls``.  If you want to know
*which* :program:`ls` is being run we have to hunt along the
:envvar:`PATH` ourselves to find it.

On the other hand, if you explicitly run a command with a specific
pathname element, say, ``./bin/ls`` then whilst ``argv[0]`` is still
what you typed, we can derive the full pathname from ``argv[0]``
itself.  :manpage:`realpath(3)` is your friend, here, and you'll get
back some ``/path/to/bin/ls``.

You can figure it out yourself without :manpage:`realpath(3)` as
``argv[0]`` will be either an absolute pathname or will require the
melding of the current working directory and ``argv[0]`` resolving
symlinks and flattening out any :file:`.` and :file:`..` elements
along the way.

In the meanwhile, :program:`ls` (probably) doesn't much care where the
binary was when it was launched.  If I copy :file:`/usr/bin/ls` to my
home directory and then run ``$HOME/ls`` I'll still get a listing.

On the other hand, we might care a little bit more about which
executable has been launched as for multiple installations we would
expect to have some installation-specific library files nearby.  If we
had been launched as :file:`.../bin/idio` then we would probably
expect to have :file:`.../lib` with a complement of library files.

That's important in development as new features in the executable are
likely to go hand in hand with the use of those new features in the
library files.

That's not quite always true, though.  If we have been installed in a
(operating system-dependent) formal place then we would expect our
library to be in a corresponding (operating system-dependent) place
which isn't necessarily in a parallel directory.

In :lname:`Linux`, you might install executable files in
:file:`/usr/bin` and have library files installed in
:file:`/usr/lib/{app}/` and ancillary files in
:file:`/usr/share/{app}` or elsewhere.

Here, of course, we have a dichotomy between the "stock" installed
library files and the bespoke instance-specific library files.  Which
ones do we use?

Both, probably.

The essence of the issue is that if you have run an explicit
pathname(d) executable then the associated libraries should be
*prefixed* to any existing :var:`IDIOLIB`.

Of course, if we don't have an :var:`IDIOLIB` when we start up then we
should create on with the operating system appropriate library
location.

Note, however, that ``argv[0]`` cannot be relied upon to actually be
the name of the executable.  I'm sure many of us have written a
"pretty name" tool to replace the otherwise indistinguishable command
names in :program:`ps` output.  We'll be cursing ourselves now!

What else can we use?

/proc
^^^^^

Many Unix systems have a :file:`/proc` filesystem which has useful
information about running processes.  :file:`/proc` has no standard
format and so the appropriate entry to probe for is operating
system-dependent.  There's more details `here
<https://stackoverflow.com/questions/933850/how-do-i-find-the-location-of-the-executable-in-c>`_
and `here
<https://stackoverflow.com/questions/1023306/finding-current-executables-path-without-proc-self-exe>`_
amongst others, no doubt.

caveats
^^^^^^^

.. sidebox::

   Yes, this is something of a race condition as the very first thing
   the code does is try to figure out where it is.  However, that's
   the very nature of race conditions, it might happen *this* time.

One problem that both ``argv[0]`` and :file:`/proc` suffer from is the
(legitimate) use of :manpage:`unlink(2)` to remove the running
executable from the filesystem.  Maybe the :file:`/proc` variant might
survive that experience but we won't be able to :manpage:`stat(2)`
anything we lookup on the :envvar:`PATH` based on ``argv[0]``.

There's no particular answer to that as there is no answer to the
"pretty name" variant.  From this we recognise we must handle no valid
answer.

What's the answer in this case, then?  Firstly print out a warning
that *something awful* has happened.  Then I guess we have to use the
operating system-dependent default values and trust that the user can
identify the external issue.

Is it likely?  Well it's not uncommon for *Continuous Integration*
systems to delete build artifacts, including target executables,
before moving onto a test stage.  All they would need to do is run
that cleanup stage in parallel with the test stage, for efficiency
reasons, and suddenly we're at risk.

Another problem is if :manpage:`chroot(2)` has been called in between
the :manpage:`exec(2)` and us trying to resolve the real path.  That's
*unlikely* to be us...isn't it?

Again, there's not much to be doing here other than use a fallback.

Variables
=========

What variables, in addition to a potential :envvar:`IDIOLIB`, should
we be looking at creating?  There's potential complications here
between "shell" and environment variables and what `POSIX thinks of
them <https://pubs.opengroup.org/onlinepubs/9699919799/>`_.

Here, we're don't particular feel bound by POSIX but we do want to be
good neighbours.  *We* might be able to handle environment variable
names with "non-portable" characters in them, notably hyphens -,
U+002D (HYPHEN-MINUS), but other users of the environment might not.

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

     .. sidebox::

	This should say "set to the current user's login shell" but I
	haven't added the :manpage:`getpw*(3)` methods yet.

     I suggest we leave alone.

:var:`IDIO_CMD`

     (shell variable)

     This is ``argv[0]`` as :lname:`Idio` sees it.  It probably isn't
     useful but maybe someone wants to know how the command was
     invoked.

:var:`IDIO_EXE`

     (shell variable)

     This is the kernel or ``argv[0]`` derived full pathname of the
     running executable.

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

:var:`HOSTNAME`

     (shell variable)

     the ``nodename`` field of a ``struct utsname`` from :manpage:`uname(3)`

     See also :ref:`libc/idio-uname <libc/idio-uname>`.

:var:`PID`

     (shell variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getpid(2)`

:var:`PPID`

     (shell variable)

     :type: ``libc/pid_t``

     the result of :manpage:`getppid(2)`

:var:`UID`

     :type: ``libc/uid_t``

     * accessing calls :manpage:`getuid(2)`

     * setting calls :manpage:`setuid(2)`

:var:`EUID`

     :type: ``libc/uid_t``

     * accessing calls :manpage:`geteuid(2)`

     * setting calls :manpage:`seteuid(2)`

:var:`GID`

     :type: ``libc/gid_t``

     * accessing calls :manpage:`getgid(2)`

     * setting calls :manpage:`setgid(2)`

:var:`EGID`

     :type: ``libc/gid_t``

     * accessing calls :manpage:`getegid(2)`

     * setting calls :manpage:`setegid(2)`


Computed Variables
------------------

:var:`SECONDS`

     (shell variable)

     :type: integer

     The number of seconds since the VM was started.

     .. note::

	There is no set method for this variable.

.. include:: ../../commit.rst


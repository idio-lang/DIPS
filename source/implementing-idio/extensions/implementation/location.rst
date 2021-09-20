.. include:: ../../../global.rst

.. _`extensions location`:

###################
Extensions Location
###################

Where to put stuff is (finally) being recognised as a thing.

In the Beginning, there was only one disk and it was full.  So stuff
spilled over into any `handy spare space
<https://en.wikipedia.org/wiki/Unix_filesystem>`_.

Wherever you put it, though, it was always the same kind of stuff, the
same kind of binaries because they were all running on your computer.

With the advent of networked file systems you immediately begin to
hit, at the very least, version issues between the sharing systems.
If you then threw a different kind of machine into the mix then you
were in heaps of trouble.

Skipping history, in the modern age we can use QEMU_ to run:

    operating systems for any machine, on any supported architecture

Now we're in real trouble!  And yet, amazingly, we still install
executables in :file:`/usr/bin` and libraries in :file:`/usr/lib` --
albeit there's been a concession to use :file:`/usr/lib64` for 64-bit
libraries.

It's still pretty hopeless.

Multiarch
=========

.. sidebox::

   :manpage:`file-hierarchy(7)` differs from :manpage:`hier(7)` (which
   is available on the \*BSDs as well) which describes the current
   layout.

There are attempts to do better and :manpage:`file-hierarchy(7)`
(Linux or :program:`systemd`-systems only?)  references the `File
System Hierarchy
<http://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html>`_ and the
`XDG Base Directory Specification
<http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_
and the Debian `Multiarch Architecture Specifiers (Tuples)
<https://wiki.debian.org/Multiarch/Tuples>`_ amongst others.

Operating Systems take differing views on the detail, :lname:`Fedora`
sticks with :file:`/usr/lib64` for the suggested ``$libdir``
(``systemd-path system-library-arch``) whereas :lname:`Ubuntu` goes
all in with :file:`/usr/lib/x86_64-linux-gnu` and
:file:`/usr/lib/aarch64-linux-gnu`, for example.  My Raspberry Pi 3B+
(standard unit of computing) reports
:file:`/usr/lib/arm-linux-gnueabihf` with the ``eabihf`` part
reflecting that it is a (little endian 32-bit) "ARM EABI, hard-float"
-- which I don't think you need me to explain....

Those tuples don't feel particularly easy to derive without asking
:program:`systemd-path` (or ``gcc -print-multiarch`` (since 4.9), I
see) and stashing the results.

With the multiarch work, though:

    The existing proposals allow for the co-installation of libraries
    and headers for different architectures, but not (yet) binaries.

which rather seems to defeat the point.

Not that I have any particular answer, I can only report what I see.

.. rst-class:: center

\*

For my own sins I did do some work with shell script wrappers where
everything that is architecture-dependent is installed in an
architecture-dependent directory leaving the question of, how do I
know what to run?

Easy!  For every executable you expect to be run you create a link for
the named executable to the wrapper script in :file:`.../bin`, the
place on your :envvar:`PATH`.

When you run the command, you are really running the wrapper script
which figures out where it is, :file:`...`, and then calculates any
appropriate set of related environment variables, say,
:envvar:`LD_LIBRARY_PATH` with architecture-dependence included and
:envvar:`PERL5LIB`, and then runs the architecture-dependent
executable.

For example, :file:`.../bin/{foo}`, on an x86_64 system, might figure
out:

* an :envvar:`LD_LIBRARY_PATH` of :file:`.../lib/x86_64`

* a :envvar:`PERL5LIB` of :file:`.../lib/perl5`

* and the real command to be run, :file:`.../bin/x86_64/{foo}`, and
  runs it with all the original arguments intact.

You can imagine all sorts of:

* operating system binary compatibility rules can be played out -- in
  my case ``SunOS-sparc-5.10`` systems could run ``SunOS-sparc-5.9``
  executables and ``SunOS-sparc-5.8`` executables and ...

* and some reasonably sensible rules to avoid rewriting environment
  variables unnecessarily if :file:`.../bin/foo` was likely to call
  :file:`.../bin/bar` -- you could update :envvar:`PATH` to point
  directly at :file:`.../bin/x86_64` in preference to :file:`.../bin`
  as :envvar:`LD_LIBRARY_PATH` is now correct.

It also had the handy (for filthily casual sysadmins *[\*cough\*]*)
property of allowing you to :program:`tar` the whole :file:`...`
hierarchy up and drop it anywhere on any other (compatible) system and
it would just work.

.. rst-class:: center

\*

The ultimate trick, there, though, was replacing the executable with a
shell script.  They don't take very long to run and can figure out a
lot of stuff.

Nothing seems to be being proposed which has the same functionality,
hence we're tied to binaries in :file:`/usr/bin` and if you stomp over
it with a binary from a different architecture then, uh, *User Error*.

Plenty of people have been looking at the problem from which you
conclude there is some nuance I am not appreciating.

.. rst-class:: center

\*

The one thing the multiarch work does do is address the disparate
:abbr:`ABI (Application Binary Interface)`\ s with a `variant of the
GNU triplet <https://wiki.debian.org/Multiarch/Tuples>`_, something
like ``x86_64-linux-gnu``.

That gives us an :samp:`{ARCH}` variant to distinguish this
architecture from some other architecture.

Versions
========

We also have some version numbers to throw into the mix.
:lname:`Idio` has a version number, say, :samp:`{IDIO_VER}`, and your
extension has a version number, say, :samp:`{EXT_VER}`.

You would think we ought to be able to have more than one version of
:lname:`Idio` installed -- think :program:`python2.7` and
:program:`python3.9`, say, which, each in turn, use
:file:`/usr/lib/python{ver}/site-packages` and
:file:`/usr/lib64/python{ver}` on my system.

And you'd like to think you can have multiple versions of your
multi-featured yet remarkably stable :samp:`{foo}` extension module at
the same time.

Ideally, then, the path to our shared library should involve all of
the above, something like
:samp:`.../lib/idio/{IDIO_VER}/foo/{FOO_VER}/{ARCH}/libfoo.so`.

Some immediate thoughts:

#. that doesn't look great -- but what do you care, this is for a
   machine

#. you don't really want users to have to second guess any of that,
   :file:`.../lib/idio` ought to be enough for a user and the machine
   can figure out the rest

#. the positioning of :file:`/{ARCH}/` is contentious (even to me!).

   Take :lname:`GCC`, for example, which has followed
   :manpage:`file-hierarchy(7)`'s suggestion to use a subdirectory of
   :file:`/usr/lib` (specifically, rather than :file:`$libdir`) for
   its own nefarious purposes then chosen :samp:`/{ARCH}/{MAJOR}/`
   where :samp:`{ARCH}` is a multiarch form even on a non-multiarch
   system (eg, Fedora where it uses a GNU triplet).  That hierarchy
   does include header files.

   That seems too high up for :file:`{ARCH}` where much of the use is
   for architecture-independent :file:`.idio` files, so push it
   further down.

   :lname:`Python3` uses something like:

       :file:`$libdir/python3.9/lib-dynload/{EXT}.cpython-3.9-{ARCH}.so`

   albeit the :file:`{EXT}` is often :file:`_{EXT}` to distinguish the
   shared library extension from any pure-:lname:`Python` code which
   is likely to be in :file:`$libdir/python3.9/{EXT}.py` (and various
   :file:`$libdir/python3.9/__pycache__/{EXT}.cpython-3.9[.{opt-n}].pyc`
   byte-compiled files).

#. and just where is :file:`...` anyway?  I imagine most people have
   their sights set on :file:`/usr/lib` (or :file:`/usr/lib64`) but it
   could be somewhere more centrally managed or shared like:

   * :file:`/usr/local` -- albeit the \*BSDs like to use
     :file:`/usr/local` as the installation point of choice for their
     :manpage:`ports(7)` packages treating it as a (genuinely) local
     filesystem that the OS has full control over

   * :file:`/opt` -- which SunOS likes to use for third party package
     installs (let's not start on the multitude of
     :file:`/usr/{collection}` trees to keep your :envvar:`PATH` full
     and busy)

   * :file:`$HOME` on a network filesystem or, better,
     :file:`$HOME/.local` for some XDG compliance

In fact, how might *we* figure any of that out?

Elsewhere, for shared libraries

* :lname:`Perl` uses something like
  :file:`{$libdir}/perl5/auto/{ext}/{ext}.so` (where :file:`perl5`
  might be variants of :file:`perl5/{PERL5_VER}`) except SunOS where
  it is generally in :file:`/usr/perl5/{PERL5_VER}` and uses
  :file:`lib/{arch-tuple}/auto/{ext}/{ext}.so` and
  :file:`{arch-tuple}` is a variation on the theme of the Debain
  multiarch, above.

.. aside::

   I think, I haven't got any to test with!

* :lname:`Python` uses a more straight-forward system for `building C
  extensions <https://docs.python.org/3/extending/building.html>`_
  where it is :file:`{PYTHONPATH-dir}/{ext}.so` -- except where
  they're not, see above.

Idio
----

In the first instance, since :program:`idio` is running, it ought to
know its own version number, :samp:`{IDIO_VER}`, although we have a
bootstrap issue of which version of :lname:`Idio` will we run when we
type :program:`idio`?

Python solves that by having :file:`/usr/bin/python` be a symlink to
:file:`/usr/bin/python3` which is a symlink to
:file:`/usr/bin/python3.9`.  You need to explicitly run
:file:`/usr/bin/python2` etc. to get the older :lname:`Python`.

In fact, Python's `virtualenv
<https://docs.python.org/3/tutorial/venv.html>`_\ s create a similar
set of symlinks in :file:`.../venv/bin` (albeit using a different
schema).

Of interest is the value of :samp:`{IDIO_VER}`.  In Python's case it
is a :samp:`{major}.{minor}` number yet my ``python --version``
reports "Python 3.9.6" and, presumably, has a more specific version
number than that, too, see :ref:`version numbers`.

Extension
---------

Slightly more problematically, is deriving the version number of the
extension, ``foo``, here, :samp:`{FOO_VER}`.  You guess we started
with something like ``load foo`` so how do we get to
:samp:`{FOO_VER}`?

Here, I think, we need some concept of a "latest" -- which, I admit,
is probably the wrong word but we've started so let's continue the
thought.  Suppose we have a bit of a development frenzy and install
several versions of ``foo``:

* :samp:`.../lib/idio/{IDIO_VER}/foo/FOO_VER1/{ARCH}/libfoo.so`

* :samp:`.../lib/idio/{IDIO_VER}/foo/FOO_VER2/{ARCH}/libfoo.so`

* :samp:`.../lib/idio/{IDIO_VER}/foo/FOO_VER3/{ARCH}/libfoo.so`

.. aside::

   *Would never happen!* you cry.

and then decide that :samp:`FOO_VER3` is a bit rubbish and re-deploy
:samp:`FOO_VER2`.

We would expect that anyone invoking ``load foo`` will get
:samp:`FOO_VER2` and so something has to say :samp:`FOO_VER2` is
the latest to be deployed -- *whatever* the possible versions,
especially as :samp:`FOO_VER3` sorts higher than :samp:`FOO_VER2`
(however it is that you manage to sort version numbers).

Clearly, there needs to be a loading mechanism to support loading
:samp:`FOO_VER3` specifically (crazy fools!) which might, *\*thinks
for too little time\**, look like :samp:`load foo@FOO_VER3`.  Of
course, anyone loading an explicit version will not be able to take
automatic advantage of the newest shiny :samp:`FOO_VER4` which will
solve all known problems when it is finally released.  Indeed, you
will never know it is running against an outdated version.

So we can imagine a bunch of
:samp:`.../lib/idio/{IDIO_VER}/{ext}/latest` files which contain, say,
:samp:`{EXT_VER}` -- or, better, :samp:`{ext}@{EXT_VER}` -- to
indicate the latest deployed version which is actually
:samp:`.../lib/idio/{IDIO_VER}/{ext}/{EXT_VER}/{ARCH}/lib{ext}.so`.

All good.

Double Trouble
^^^^^^^^^^^^^^

But wait!  Suppose we now release another version :lname:`Idio`?  Or,
more perniciously, another spin on the existing :samp:`{IDIO_VER}` if
it takes the form :samp:`{major}.{minor}` like :lname:`Python`.  Here,
I'm thinking in :lname:`Python` terms of a 3.9.7 release updated from
the 3.9.6 we have installed but both bearing the same 3.9
:samp:`{IDIO_VER}`.

That's *bound* to change many of those :file:`latest` files to
whatever is the latest bits.  But the previously installed
:samp:`idio.{major}.{minor}` won't be expected those (newer) extension
releases.  If you're very careful not to change any of the internals
of :lname:`Idio` then it'll probably work -- until it doesn't.
Tricky.

.. aside::

   There can only be one!

Or is it?  As we can only install a single binary in :file:`/usr/bin`
then we *will* have overridden that previous
:samp:`idio.{major}.{minor}` executable.

Is it the only :samp:`idio.{major}.{minor}` executable on the system,
though?  Is it the only :samp:`idio.{major}.{minor}` executable using
the deployed :file:`.../lib/idio/{IDIO_VER}` hierarchy?

To avoid disappointment you have to mandate that only the
:file:`/usr/bin/idio` executable (for some :samp:`{IDIO_VER}`) can use
the :file:`$libdir/idio/{IDIO_VER}` hierarchy -- or, at least, the
only to use it without risk.

:lname:`Python` gets away with that as almost everything is a symlink
to the (only) one true :program:`python.3.9` executable.

If you want to deploy a :file:`.../bin/idio` then you'll need to
deploy a :file:`.../lib/idio/...` hierarchy.

:lname:`Python` does do that with its virtualenvs giving, say:

* :file:`.../venv/bin/python` (a symlink, eventually, to
  :file:`/usr/bin/python3.9`)

* :file:`.../venv/lib/python3.9/site-packages`

Multiple Installations
""""""""""""""""""""""

.. aside::

   Curiously, English dictionaries are a little reticent about "have a
   nosey" rather than "(being) nosey".  I've linked to an
   English-Spanish dictionary as it was the first hit I had.

In a previous life, when GNU_ software was changing fairly rapidly, I
reached the stage of installing new releases in separate hierarchies
in :file:`/usr/local`, so, :file:`/usr/local/emacs-{ver}`, say, and
updated startup scripts to `have a nosey
<https://www.wordreference.com/es/translation.asp?tranword=have%20a%20nosey>`_
and allow people to pick up the latest bits and others could stick
with a stable release.

In the modern age of packaged installs, people compiling software is a
rarity and we are forced into the single instance :file:`/usr/bin`
`cul-de-sac
<https://www.collinsdictionary.com/dictionary/english/cul-de-sac>`_.

Mixed Releases
""""""""""""""

I have wondered about a slightly different approach where, at
deployment time, you might create a *build*-specific
:file:`.../lib/idio/{IDIO_BUILDVER}/latest` containing a list of *all*
the extension releases, say, :samp:`foo@FOO_VERx` and
:samp:`bar@BAR_VERy` and :samp:`baz@BAZ_VERz`, each appropriate to
that :samp:`{IDIO_BUILDVER}`.

If :lname:`Idio` didn't know about an extension at the time of
deployment then you would derive the extension version number from its
:file:`latest` file -- what else have you got to go on?

This method would allow multiple :samp:`{IDIO_BUILDVER}` to work
alongside one another but neither could take useful advantage of any
newer :samp:`{EXT_VER}` than their :file:`latest` files allowed
without risking invoking some far more advanced release of code.

Virtualenvs
"""""""""""

We are rolling back around to that sort of :lname:`Python`-esque
virtualenv system where we use a system installed executable but we
pick up the virtualenv-specific installed extensions in preference.

Now we have to be a bit more careful when resolving where we are.


Shared Library
--------------

A final note is that it is common practice for files in the standard
system library directories -- and, presumably, for all libraries as
part of standardized packaging instructions -- to follow the `shared
library naming conventions
<https://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html>`_
resulting in a *linker name*, :file:`libfoo.so`, being a symlink to
the *soname* (shared object name), :file:`libfoo.so.{major}`, which is
a symlink to a *real name*, :file:`libfoo.so.{major}.{minor}[.{rev}]`.

In this format, :file:`{major}` is updated for interface-breaking
changes, :file:`{minor}` is for updates to :file:`{major}` and
:file:`{rev}` is the revision of :file:`{minor}`.

In principle, :file:`/usr/lib64/libc.so` is a symlink to, say,
:file:`/usr/lib64/libc.so.2.33` although as I test that this Fedora
system has :file:`libc.so` as "GNU ld script":

.. code-block:: text

   /* GNU ld script
      Use the shared library, but some functions are only in
      the static library, so try that secondarily.  */
   OUTPUT_FORMAT(elf64-x86-64)
   GROUP ( /lib64/libc.so.6 /usr/lib64/libc_nonshared.a  AS_NEEDED ( /lib64/ld-linux-x86-64.so.2 ) )

which suggests to use of :file:`/lib64/libc.so.6` which is a symlink
to :file:`libc-2.33.so`.

So, "along those lines", then.

.. rst-class:: center

   \*

For added fun, :program:`libtool` uses a different version numbering
scheme involving `more precise backwards compatibility
<http://www.gnu.org/software/libtool/manual/html_node/Libtool-versioning.html>`_.

.. _`where are we`:

Where Are We?
=============

I often install bundles where you want to pick up items related to the
executable being run.  If you know this executable is
``.../bin/idio``, say, then you can find the libraries that *this*
executable was meant to run with in :file:`.../lib/idio`.

This gives your bundle the air of *position independence* which is
extremely useful if you have multiple, potentially incompatible,
versions lying around.  Even better when you can :program:`tar` the
bundle up and drop it elsewhere and have it just work.

This sort of position independence is similar to the
:lname:`Python`-style *virtualenv* and RedHat *Software Collections*
both of which require that you explicitly run a command to "activate"
the new environment.  I've always preferred the idea that running a
command should be enough to activate the environment on its own.

That brings up a bit of a dance around auto-updating environment
variables which is influenced by whether or not environment variables
have been set at all.

There are two "executable" pathnames of interest, here:

#. the pathname you executed by dint of the specific executable you
   ran (:file:`./bin/idio` or :file:`/path/to/bin/idio`) or is found
   on your :envvar:`PATH` either of which, in the case of
   bundles/virtualenvs, might be a symlink (or chain of symlinks) to
   the real executable

#. the real executable

   Which, when you're not using a bundle/virtualenv, is probably the
   same as the first value.

For example, suppose I have created an XDG approved
:file:`$HOME/.local/bin/idio` symlink to a real deployed executable
:file:`/path/to/deployed/bin/idio` and that :file:`$HOME/.local`
hierarchy contains your favourite :lname:`Idio` extensions in
:file:`$HOME/.local/lib/idio`.

If I run, via :envvar:`PATH` or directly,
:file:`$HOME/.local/bin/idio` I would expect to see both
:file:`$HOME/.local/lib/idio` and :file:`/path/to/deployed/lib/idio`
on :envvar:`IDIOLIB`.

In particular, :file:`$HOME/.local/lib/idio` *before*
:file:`/path/to/deployed/lib/idio`.

There's a slight variation for system executables (in :file:`/usr/bin`
or :file:`/bin`) as the system will expect their library files to be
in :file:`$libdir` (:file:`/usr/lib64` or
:file:`/usr/lib/x86_64-linux-gnu` or wherever) but we can deal with
that.

The question is, where does any existing :envvar:`IDIOLIB` fit with
respect to these to, executable-oriented paths?

My bundling belief is that the executable-orientated paths should be
before any existing :envvar:`IDIOLIB`.

See the commentary on virtualenvs, below, as well.

Figuring out the pathname of the currently running executable is a
non-trivial exercise with plenty of operating system-bespoke special
cases and with the potential for no useful result whatsoever.

argv[0]
-------

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

Unfortunately, resolving symlinks hides the pathname to the original
``argv[0]`` which will be a problem for virtualenvs.  So we'll need to
figure out a "normalized" ``argv[0]`` (not resolving symlinks) and a,
maybe different, maybe not, "resolved" ``argv[0]`` (which has resolved
symlinks).

In the meanwhile, :program:`ls` (probably) doesn't much care where the
binary was when it was launched.  If I copy :file:`/usr/bin/ls` to my
home directory and then run ``$HOME/ls`` I'll still get a listing.

On the other hand, we might care a little bit more about which
executable has been launched as for multiple installations we would
expect to have some installation-specific library files nearby.  If we
had been launched as :file:`.../bin/idio` then we would probably
expect to have :file:`.../lib/idio` with a complement of library
files.

That's important in development as new features in the executable are
likely to go hand in hand with the use of those new features in the
library files.

The essence of the issue is that if you have run an explicit
pathname(d) executable then the associated libraries should be
*prefixed* to any existing :var:`IDIOLIB`.

Of course, if we don't have an :var:`IDIOLIB` when we start up then we
should create one with the operating system appropriate library
location.

Note, however, that ``argv[0]`` cannot be relied upon to actually be
the name of the executable.  I'm sure many of us have written a
"pretty name" tool to replace the otherwise indistinguishable command
names in :program:`ps` output.  We'll be cursing ourselves now!

What else can we use?

/proc
-----

Many Unix systems have a :file:`/proc` filesystem which has useful
information about running processes.  :file:`/proc` has no standard
format and so the appropriate entry to probe for is operating
system-dependent.  There's more details `here
<https://stackoverflow.com/questions/933850/how-do-i-find-the-location-of-the-executable-in-c>`_
and `here
<https://stackoverflow.com/questions/1023306/finding-current-executables-path-without-proc-self-exe>`_
amongst others, no doubt.

caveats
-------

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

Virtualenvs
-----------

What happens with a virtualenv?

We are going to run :file:`.../bin/idio`, or, possibly,
:file:`.../bin/{link}`, which will be a symlink to, say,
:file:`/usr/bin/idio` (or some other deployed executable).  Or it
could be a chain of symlinks (think: :file:`python` to :file:`python3`
to :file:`python3.9` to :file:`/usr/bin/python3.9`) for which we
ignore all the intermediaries.  We're just looking at
:file:`.../bin/idio`, the original script interpreter and
:file:`/usr/bin/idio` the actual executable.

We will want to have both :file:`.../lib/idio`, the "virtualenv
libraries", and :file:`$usrlib/idio` (or whatever is appropriate for
the system), the "executable libraries", on :envvar:`IDIOLIB`.

Obviously, if :file:`.../bin/idio` is a symlink to
:file:`/path/to/bin/idio` then we be looking for :file:`.../lib/idio`
and :file:`/path/to/lib/idio` to be used.

Here's a subtlety, though, suppose you have set :envvar:`IDIOLIB`
before you start.  I think the result should be (broadly):

    :file:`{venv_lib}:{exe_lib}:{IDIOLIB}`

That is any virtualenv and executable libraries should *prefix* any
existing :envvar:`IDIOLIB` -- *even if* :envvar:`IDIOLIB` already
contains :file:`{venv_lib}` or :file:`{exe_lib}`

I think I would rather protect the integrity of the script being run
(which is expecting particular library suites in :file:`{venv_lib}`
and :file:`{exe_lib}`) than accommodate astute users.  The more adept
can work their way around anyway.

I'm thinking in terms of multiple virtualenvs, A, B and C, where each
call commands from the other.

.. rst-class:: center

   \*

The one thing you may (will?) end up with is repeated prefixing (or
suffixing) of library paths.

Historically, I've written a ``trimpath`` function to re-write any
colon-separated PATH-style variable with its equivalent without
repetitions.  A useful tool in the bag that's worth adding, I think.

.. rst-class:: center

   \*

If :file:`.../bin/idio` is a hard link to an executable, this doesn't
work.  It is not (usefully) possible to determine the other name(s)
for the executable (the other reference(s) to the inode) and even if
we did pause the bootstrap to search the entire filesystem we can't
reliably determine which is the one true name if all have a
corresponding :file:`lib` directory.

The upshot is that if we :manpage:`stat(2)` ``argv[0]`` (or the
:manpage:`realpath(3)` version of it) and it is a symlink then we need
to add the corresponding :file:`lib` hierarchy to :envvar:`IDIOLIB`
followed by the corresponding :file:`lib` directory associated with
the resolution of :manpage:`readlink(2)` of the original interpreter.

.. include:: ../../../commit.rst


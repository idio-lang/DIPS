.. include:: ../../global.rst

.. _`process substitution`:

********************
Process Substitution
********************

Rather than the similarly named *Command Substitution*, where we want
to substitute the collected output of a command, with *Process
Substitution* we want to substitute a filename for another command to
use where the filename is really a pipe to a process.

This is a rather subtle distinction but the obvious use case is where
an external command would be expecting a filename and not the contents
of a file:

.. code-block:: console

   $ cat file
   This is a file

If you were to give :program:`cat` the contents of :file:`file` then
it won't be very happy:

.. code-block:: console

   $ cat $(cat file)
   cat: This: No such file or directory
   cat: is: No such file or directory
   cat: a: No such file or directory
   This is a file

.. note::

   Note that the file, :file:`file`, contains its own name in its
   contents, hence the last line.

which leaves us with the, slightly tautological:

.. code-block:: console

   $ cat <(cat file)
   This is a file

where the "outer" ``cat <(...)`` is, in practice, something like ``cat
/dev/fd/63`` and :file:`/dev/fd/63` is attached to the output of the
(asynchronous) command ``cat file``.

The, rather more understandable, canonical example is:

.. code-block:: console

   $ diff <(sort fileA) <(sort fileB)

which is a very powerful expression.  Is it a form of process
meta-programming?  Maybe.

External commands are not the only use, I frequently use Process
Substitution in loops:

.. code-block:: bash

   while read line ; do
       ...
   done < <(cat file)

which has the ever so subtle advantage of keeping the ``while``
statement in the current shell so that it can modify any local
variables in the loop.  Compare with:

.. code-block:: bash

   cat file | while read line ; do
       ...
   done

where the ``while`` is in a subshell (because of the ``|``).

.. rst-class:: center

\*

So there's a few things to do:

#. we have to recognise the command we are going to run for Process
   Substitution

#. we need to run it

#. we need to marry this up with a (possibly named) pipe

(Named) Pipes
=============

You would think this would be the easy bit but oh, no!

In the first instance, it would be nice to use the :file:`/dev/fd/{N}`
format as it clearly represents what it is and has the nice advantage
that the operating system maintains it and we don't have to run around
creating and removing files in the filesystem.

.. sidebox::

   Clearly, there will be some operating system process-indirection
   involved as we can't be having people poking each others'
   :file:`/dev/fd/0` file descriptors.

In essence, if we create a :manpage:`pipe(2)` for inter-process
communication then each of the pipe's file descriptors will have a
:file:`/dev/fd/{N}` entry associated with it.

For those systems that don't support :file:`/dev/fd` then we'll have
to create a true named pipe, a FIFO, see :manpage:`mkfifo(2)`, and use
its name instead.

.. note::

   The nomenclature isn't always consistent but let's try to use a
   FIFO to mean the filesystem-oriented pipe.  Once opened, the entry
   in the filesystem has no bearing on the functionality of the pipe.

   We'll use named pipe to indicate we intend to use a pathname to
   coordinate access which may or may not be an actual FIFO.

Of course, the reason that's important is that not all operating
system play the same game.  :lname:`Bash` let's us easily take a look
at its thoughts:

.. code-block:: console

   [Linux   ]$ ls -l <(echo "hello")
   lr-x------. 1 idf   idf        64 Jun 11 12:14 /dev/fd/63 -> 'pipe:[1781424]'

   [SunOS   ]$ ls -l <(echo "hello")
   crw-rw-rw-  1 root  root  578, 63 Jun 11 12:15 /dev/fd/63

   [Mac OS X]$ ls -l <(echo "hello")
   prw-rw----  0 idf   staff       0 11 Jun 12:16 /dev/fd/63

   [FreeBSD ]$ ls -l <(echo "hello")
   prw-------  1 idf   wheel       0 Jun 11 12:17 /tmp//sh-np.OrAlUF

Hmm.  There's a few things to digest there.

.. sidebox::

   There's a little bit of bootstrap artiface going on here as
   :lname:`Bash`'s test for some functionality it is about to compile
   requires a shell that is able to implement the test.

.. aside::

   :program:`m4`?  *Cripes*, I'd forgotten about that.

First up, FreeBSD doesn't use the :file:`/dev/fd` form.  Well,
careful, it *does* for file descriptors 0, 1 and 2 but not for
anything else.  :lname:`Bash` figures this out with a judicious ``exec
test -r /dev/fd/3 3</dev/null`` in :file:`aclocal.m4`.  On the plus
side, it is a pipe.

Of the operating systems that do support :file:`/dev/fd` you'll notice
they are all using file descriptor 63.  That's because :lname:`Bash`
chooses to:

    Move the parent end of the pipe to some high file descriptor, to
    avoid clashes with FDs used by the script.

    --- ``process_substitute()`` in :file:`subst.c`

I guess that defers the problem with users having to guess which file
descriptors are free when they want to stash a file descriptor, as in
``exec >&3``, and generally just plumping for a low numbered one, as
in 3.  Too bad if that was important.

SunOS is a bit more interesting, :file:`/dev/fd/63` is a character
special device (and owned by *root*).  In fact, many (all possible?)
:file:`/dev/fd/{N}` exist.  I guess you're meant to know your own file
descriptors (which doesn't seem *that* unreasonable).

Mac OS X is possibly the most honest in that :file:`/dev/fd/63` is a
(named) pipe.

Linux has :file:`/dev/fd/63` be a symlink to what we presume must be a
pipe.  ``ls -lL`` confirms that.

Running
=======

Running the command, married up to a (named) pipe should have the
heavy work done already.  We have ``pipe-into`` and ``pipe-from``
mechanisms from the :ref:`pipeline meta-commands <pipeline
meta-commands>` work so, presumably, we can extend that with
``named-pipe-into`` and ``named-pipe-from`` variants which will return
a pathname rather than a pipe handle.

In terms of how and when we do all this it ought to come out in the
wash as:

.. code-block:: idio

   ls -l <{ echo "hello" }

is just a regular function call where we evaluate each argument in
turn (with ``ls`` and ``-l`` just being symbols) and ``<{ echo "hello"
}`` is another argument.  So long as the evaluation of ``<{ ... }``
results in a pathname to a named pipe (:file:`/dev/fd` or otherwise)
then we're good to go.

But not so good to stop.  Let's have a think.

The trickier bit is arranging the longevity of the pipe's name.  Well,
the *name* should be easy enough but I mean, for example, in the case
of having established a ``pipe-from``-style sub-command then *we*
would normally use the read end of the pipe.

Except we need to be careful.  Linux says:

    If all file descriptors referring to the write end of a pipe have
    been closed, then an attempt to read(2) from the pipe will see
    end-of-file (read(2) will return 0).

    --- :manpage:`pipe(7)`

The problem is that if we close the write end of a ``pipe-from``
pipeline in the parent then Linux is at liberty to close the pipe
completely, under our feet, as soon as the asynchronous process
associated with the pipe is done.  Which is quite possibly going to be
before we get around to calling ``read-line`` on the pipe handle we
got back from launching the thing in the first place.

However, with a ``named-pipe-from`` we intend that *another*
sub-program utilise this name (although, there's no reason why *we*
shouldn't use it -- that depends on what the code says -- albeit there
is a "complication" which we discuss below).

The process attached to the named pipe, the ``echo "hello"`` part, is
only going to hang around whilst *someone* has the read end of the
pipe open.  If no-one is holding the read end open then the writer,
``echo "hello"``, will get hit by a ``SIGPIPE``/``EPIPE`` pincer
movement.  (OK, not in the case of something like ``<{ sleep 1 }`` as
it doesn't write anything but you get my drift.)

.. note::

   Technically, :manpage:`pipe(7)` on Linux says:

       If all file descriptors referring to the read end of a pipe
       have been closed, then a write(2) will cause a SIGPIPE signal
       to be generated for the calling process.  If the calling
       process is ignoring this signal, then write(2) fails with the
       error EPIPE.

Named pipes are no different in this regard.  That means there's a
sort of gap between us having:

* created the named pipe and the "writer" (``echo "hello"``)

* created the sub-process "reader" (assuming the user of the named
  pipe is an external command)

* and then the sub-process reader actually opening the named pipe

We have to hold the pipe open during this time to avoid the
``SIGPIPE``/``EPIPE`` combo.

:lname:`Bash` doesn't hold the pipe open beyond that encapsulating
expression:

.. code-block:: console

   $ ( fn=<(echo "hello"); cat $fn )
   cat: /dev/fd/63: No such file or directory

Ideally, we could pick up on some inter-expression gap but our
evaluation model of cascading function calls (aided and abetted by
templates) means we don't really have a handle on individual
expressions.

Ostensibly, our only safe point to close up is when the sub-process,
technically, the job, associated with the Process Substitution
completes.  Whether it succeeds or fails, it is complete and therefore
"done" with the pipe.

This works even if the reader of the named pipe is just more
:lname:`Idio` code.  Consider:

.. code-block:: idio

   fh := open-input-file <{ printf "hello world\n" }

Here, the ``printf ...`` part will be in a sub-process writing to the
named pipe but the read end of the named pipe is us, not a separate
program like :program:`ls`.

We can close our read end of the named pipe when the sub-process
completes.

Hence, :file:`lib/job-control.idio` maintains a table of
``%process-substitution-job`` entries, indexed by Job Control job.
Each entry is a simple structure of ``fd path dir`` where
``/dev/fd``-capable systems set ``fd`` and the other two to ``#f``.
Systems using named pipes will set ``fd`` to ``#f`` and ``path`` to
the named pipe with ``dir`` the (unique) directory the named pipe is
in.

.. note::

   Regarding both ``path`` and ``dir`` for the named pipe, recent
   linkers have begun warning about the use of :manpage:`mktemp(3)`
   which :lname:`Bash` uses through ``sh_mktmpname()`` to create a
   temporary file name which it uses as a named pipe:

       warning: the use of \`mktemp\' is dangerous, better use \`mkstemp\' or \`mkdtemp\'

   The suggested solution is to use :manpage:`mkdtemp(3)` to create a
   unique directory then create the named pipe in there.  That's fine but
   we now have to remove two things when we're done, the named pipe and
   the temporary directory.

Back in our SIGCHLD handler, if we see that a job has completed then
we can check the table of ``%process-substitution-job``\s and either
:manpage:`close(2)` or :manpage:`unlink(2)` and :manpage:`rmdir(2)`
the appropriate parts.

During final shutdown we can also do any otherwise neglected tidying
up for named pipes.  We don't care so much for the file descriptors as
they'll get closed during shutdown anyway.

:lname:`Bash` manages this with its ``fifo_list`` array in
:file:`subst.c` which it periodically trims.

.. warning::

   There's always a possibility that we won't have seen the child
   process complete *even during shutdown* in which case any
   outstanding named pipes will remain in the filesystem.

   You can contrive this with :lname:`Bash` on FreeBSD (which uses
   named pipes) with something like:

   .. code-block:: console

      $ bash -c "{ sleep 2 ; ls <(echo hello); } &"
      $ /tmp//sh-np.TixduF

   (Technically, you will have gotten your prompt back before
   :program:`ls` runs hence the prompt in ``$ /tmp//sh-np.TixduF``.)

   Here we are backgrounding the Group Command meaning that
   :program:`bash`, as in ``bash -c``, will exit leaving the
   backgrounded process, another :program:`bash`, running.

   Notice, given that the named pipe remains, that the sub-shell
   :program:`bash` is not the one tracking ``fifo_list`` so it isn't
   removed -- or there is a *exit_shell()* race condition!

   Look out for directories called :samp:`sh-np.{xxxxxx}` from
   :lname:`Bash` or :samp:`idio-np-{xxxxxx}` from :lname:`Idio` in
   :envvar:`TMPDIR` or :file:`/tmp` or wherever.

Complications
=============

There is a complication with the ``name-pipe-*`` variants.  *Process
Substitution* is meant to be for external commands to use,
:program:`diff`, :program:`cat` etc., but there's nothing to stop *us*
getting the pathname to the named pipe back.

/dev/fd
-------

However, for :file:`/dev/fd` enabled systems, that is, ones where
we've used a regular :manpage:`pipe(2)` under the hood, this pathname,
:file:`/dev/fd/{n}`, masquerades as a true pathname but is really a
contrivance.  It is not a file to be opened anew, it is *already*
open.

.. aside::

   Twice?  Control yourself, man!

Opening :file:`/dev/fd/{n}` does not even result in file descriptor
:samp:`{n}`.  In fact, opening :file:`/dev/fd/{n}` is *defined* as
being indistinguishable from calling :samp:`dup({n})` or
:samp:`fcntl({n}, F_DUPFD)`.  Opening :file:`/dev/fd/{n}` is going to
get you another file descriptor, :samp:`{m}`, and now you've got the
file open *twice*.

External Commands
^^^^^^^^^^^^^^^^^

Let's consider an example using our trusty :program:`auto-exit` test
command to write a ``named-pipe-into`` test:

.. code-block:: idio

   auto-exit -o 3 -O (named-pipe-into {
     sed -e "s/^/Boo /"
   })

from which we might get something like:

.. code-block:: console

   Boo auto-exit: 1054079: wrote line 1 to /dev/fd/8
   Boo auto-exit: 1054079: wrote line 2 to /dev/fd/8
   Boo auto-exit: 1054079: wrote line 3 to /dev/fd/8

We're about to have four processes and several copies of file
descriptors so let's see what happens.

We are *PID1* and you suspect that, at some point, we are going to
*fork* and *exec* :program:`auto-exit`.  Not before we've processed
all the arguments.  After all, it's just a complicated version of
``cmd args``.

The interesting argument is :samp:`(named-pipe-into ...)`, of course.
For this we will call ``fork-command`` in :file:`lib/job-control.idio`
which will do some prep work, fork and let the sub-:lname:`Idio`
figure out how to run ``...``.  The sub-:lname:`Idio` is *PID2*.

Before we launch it, though, the prep work is going to include a call,
by us, *PID1*, to ``libc/proc-subst-named-pipe``, in
:file:`src/libc-wrap.c`, which, as we're not on FreeBSD, is going to
return the embellished output from :manpage:`pipe(2)`.  Let's say we
get back the two pipe file descriptors, :samp:`{pr}` and :samp:`{pw}`.
The embellished form is a list of those two and their names in the
file system, :file:`/dev/fd/{pr}` and :file:`/dev/fd/{pw}`.

The important thing to remember here is that we, *PID1*, have both of
those file descriptors open.  We then fork the sub-:lname:`Idio` as
*PID2* and then it too has both of those file descriptors open.

Part of the prep work for ``named-pipe-into`` is to indicate that the
future *stdin* of the exec'd sub-process, *PID2*, is going to be
:samp:`{pr}`.  The action of prepping IO is to :manpage:`dup2(2)` the
target file descriptor to 0 and close the target.  The net effect of
that is that we still hold a file descriptor open to the read end of
the pipe that we knew as :samp:`{pr}` but it is now file descriptor 0
and file descriptor :samp:`{pr}` has been closed.

In the case of ``named-pipe-into``, the sub-:lname:`Idio`, *PID2*, is
looking to read from the pipe so it can close the write end,
:samp:`{pw}`, and, as we've not done anything else, the
sub-:lname:`Idio` will have inherited *PID1*'s *stdout*.

The sub-:lname:`Idio` can now determine what to do with ``...`` which,
in this case is a simple block with a single :program:`sed` command in
it.  Of course it could be a series of commands doing whatever but
here it is a :program:`sed` which has the conceptual advantage of
reading its *stdin* until it sees EOF.

As we know with pipes, it will get an EOF when all of the write ends
are closed.  At the moment, the sub-:lname:`Idio`, *PID2*, has closed
its copy of the write end but the original :lname:`Idio`, *PID1* still
has it open.

Let's assume the sub-:lname:`Idio` makes some progress and manages to
fork and exec :program:`sed`, now *PID3*, which inherits file
descriptors from *PID2* which include 0, which is the read end of the
pipe, and 1, the same *stdout* as everyone else.

So far, then, we have :program:`sed`, *PID3*, blocked reading from the
read end of the pipe, the sub-:lname:`Idio`, *PID2*, waiting for
:program:`sed` to finish so it can carry on with whatever is left of
``...`` and the original :lname:`Idio`, *PID1*.

Whilst all that was going on, *PID1* still has both :samp:`{pr}` and
:samp:`{pw}` open.  With its ``named-pipe-into`` hat on, the parent
:lname:`Idio` doesn't need the read end of the pipe open, so it can
close :samp:`{pr}` leaving it with just the write end of the pipe,
:samp:`{pw}` in its hands.

The parent :lname:`Idio`'s task here was to evaluate the argument
``(named-pipe-into ...)`` for which the return value is the pathname
representing the opened pipe that someone can write into.  Here, then,
it is the fourth element of the list returned from
``libc/proc-subst-named-pipe``, :file:`/dev/fd/{pw}`.

.. rst-class:: center

\*

Let's take a slight pivot at this point.  Having evaluated the
argument ``(named-pipe-into ...)``, *PID1* has created an asynchronous
command (the combination of the sub-:lname:`Idio` and its sub-process
running :program:`sed`) which it can associate with the returned named
pipe (either the file descriptor :samp:`{pw}` or the pathname of a
true named pipe).

.. rst-class:: center

\*

In terms of evaluating our original line we have:

.. csv-table::
   :widths: auto

   ``auto-exit``, a symbol.
   ``-o``, a symbol.
   3, a fixnum.
   ``-O``, a symbol.
   :samp:`%P"/dev/fd/{pw}"`, a pathname

Great!  Let's fork and exec!

We fork and exec :program:`auto-exit` as *PID4* which inherits
*PID1*'s file descriptors which include:

* 0 -- *stdin* which we're not going to use

* 1 -- *stdout* which we're not going to use because of the :samp:`-O
  {FILE}` argument

* :samp:`{pw}`

So, here in :program:`auto-exit`, *PID4*, we have :samp:`{pw}` open
but we're going to ignore it.  Instead, using :samp:`-O {FILE}`, we
will run :samp:`exec >{FILE}` meaning our *stdout* is going to
:file:`/dev/fd/{pw}`, the same place as :samp:`{pw}`, the write end of
the pipe.

.. rst-class:: center

\*

:socrates:`Hey, the write end of the pipe is open twice, what gives?`
Well, to some degree, we don't care.  Indeed, that's the nature of the
beast in passing a :file:`/dev/fd/{n}` form. The *file* (device?)
:file:`/dev/fd/{n}` only exists if file descriptor :samp:`{n}` is open
and there is no way of opening :file:`/dev/fd/{n}` without duplicating
the file descriptor.

In one sense we are reliant on the fact that we are running an
external command which will do its thing and then exit, implicitly
closing all file descriptors.  It feels a bit inelegant but, uh,
that's the way it goes.  We can sort of see the same from
:lname:`Bash` with something like:

.. code-block:: console

   $ ls -l /dev/fd/ <(sleep 1)
   lr-x------. 1 ... /dev/fd/63 -> 'pipe:[6122009]'

   /dev/fd/:
   total 0
   lrwx------. 1 ... 0 -> /dev/pts/1
   lrwx------. 1 ... 1 -> /dev/pts/1
   lrwx------. 1 ... 2 -> /dev/pts/1
   lr-x------. 1 ... 3 -> /proc/1072573/fd
   lr-x------. 1 ... 63 -> 'pipe:[6122009]'

Here, :program:`ls` has re-ordered its arguments to show
:file:`/dev/fd/63` first which is a symlink to pipe #6122009.
:program:`ls` is also showing its own :file:`/dev/fd` listing which
includes:

* :file:`/dev/fd/3`, the open directory for :file:`/dev/fd` (magically
  mapped to :file:`/proc/{PID-of-ls}/fd`) as :program:`ls` loops
  calling :manpage:`getdents(2)`

* :file:`/dev/fd/63` the Process Substitution argument which is that
  same symlink to pipe #6122009.

Now this example isn't quite right because :program:`ls` hasn't
*opened* the argument ``/dev/fd/63`` it was given (from the Process
Substitution argument ``<(sleep 1)``) but it demonstrates the file
descriptor 63 is open whilst :program:`ls` is running and that if
:program:`ls` opens its argument ``/dev/fd/63`` then it'll be using
file descriptor 4, say, *as well as* file descriptor 63.

.. rst-class:: center

\*

In the meanwhile, :program:`auto-exit` will now write three lines to
its *stdout* which, being the write end of the pipe seamlessly appear
on the *stdin* of :program:`sed` and we get our nice output.

And then it all hangs.

The problem is that, although :program:`auto-exit` wrote three lines
and quit, thus closing both its *stdout* and the inherited
:samp:`{pw}`, the write end of the pipe was inherited from *PID1*
which still has it open.  *D'oh!*

We need to have *PID1* close :samp:`{pw}` but it can't do that until
*after* it has forked :program:`auto-exit` as otherwise we'll have
closed :samp:`{pw}` and the pathname we're passing to
:program:`auto-exit` is invalid.

The twist, here, is that :samp:`{pw}` is associated with the
*argument* ``(named-pipe-into ...)`` and not the (external) command
:program:`auto-exit` so it's not even the case that we can close
:samp:`{pw}` when :program:`auto-exit` completes as we don't hold that
relationship.  :samp:`{pw}` is associated with the asynchronous
command of the sub-:lname:`Idio` and :program:`sed`, remember, and
:program:`sed` is blocked reading from the read end of the pipe
meaning that it hasn't exited indicating we are free to close
:samp:`{pw}` through the ``%process-substitution-job`` mechanism.

Classic deadlock.

Could we create such a relationship between :program:`auto-exit` and
:samp:`{pw}`?  Maybe, but the cascading nature of evaluation means
that in practice we'd be throwing a nominal "close this, will ya?" out
into the aether in the hope that it is caught and managed.

There is another way, though, which is a bit hacky so you never heard
me say this, right?  We could flag the :file:`/dev/fd/{n}` pathname we
create as special -- the sort of special that users can't abuse.  If
*PID1* were to walk along those arguments and identify any such
special pathnames it could take liberty of closing the associated file
descriptor after having forked the (external) command.

It feels slightly awful but it is quite practical.  So, uh, let's move
on.

Idio Commands
^^^^^^^^^^^^^

Hopefully, we can all now see the problem with *Process Substitution*
and :lname:`Idio` commands.  If it takes a bit of magic hackery to be
inserted between fork and exec of an external command to ensure that
*PID1* closes any special pathname argument file descriptors then who
is going to do it for regular :lname:`Idio` commands?

Ans: no one.

.. code-block:: idio

   fh := open-output-file (named-pipe-into {
     sed -e "s/^/Boo /"
   })

We now have both ``fh`` open into the asynchronous command *and* the
write end of the pipe, :samp:`{pw}`, open in *PID1*.  No-one knows to
close :samp:`{pw}` and :program:`sed` will not see EOF. *\*shakes
fist\**

To paper over this "contrived pathname and actually open file
descriptor" mess we can make ``open-output-file`` act a bit like
``open-output-file-from-fd`` and have it figure out the file
descriptor from the supplied pathname if it is a special.

``fh`` will now use the file descriptor of the special pathname,
:samp:`{pw}`, and when the user closes ``fh`` they will have closed
the last reference to the write end of the pipe and :program:`sed`
will get its EOF.

That, he says, hesitantly, seems to work... for *output* pipes.  At
least those that read their input until EOF.

For input pipes we have a slightly different problem.  What we're
asking the asynchronous command to do might not take very long:

.. code-block:: idio

   fn := named-pipe-from {
     printf "hello\n"
   }

   fh := open-input-file fn

There is race condition here between the asynchronous command being
launched and running to completion *before* we even get round to
opening the file handle, let alone reading from it or closing it.  The
open could fail even though it's the statement after the creation of
the asynchronous command.  The point being that we don't have control
over the operating system's scheduling so who knows what might happen
when a second process is in play.

Indeed, we can contrive a delayed-open command which will "sleep 1"
before invoking the open.  Here, we have no chance, the (named) pipe's
asynchronous command will (almost!) certainly have been and gone
before we call *open* which will fail with ENOENT.

In general, though, the act of opening the file handle may result in
*open* or *fcntl* system calls failing with EBADF or when we try to
*read* or *close* the file handle later we can get the same EBADF.
The pipe between us and the asynchronous command has been closed
because the writer, the asynchronous command, has quit.  Any action we
take on the read end of the pipe will get EBADF.

Oh dear.

I'm not sure there is a sensible fix for this.  If you associate an
asynchronous command with a input pipe and then you delay opening,
reading or closing the pipe then the asynchronous command could have
completed and you're going to get EBADF errors.

Hiccup
""""""

There is a minor "dotting the i's and crossing the t's" problem in
that the default open modes for ``open-input-file`` and
``open-output-file`` are ``re`` and ``we`` respectively but the
underlying :manpage:`pipe(2)` does not have the ``O_CLOEXEC`` flag
set.

The obvious action is to disable that default "e" flag (and set the
handle's type to be a pipe).  However, had the user called
``open-file``, say, with an explicit mode including "e" then we will
have upset their expectations.

So, update the code with a flag as to whether the user supplied the
mode or not and remove the *CLOEXEC* component if they didn't.

FIFOs
-----

That tricksome hackery involved with :file:`/dev/fd/{n}` contrived
pathnames doesn't mean we can remove our ``%process-substitution-job``
mechanism, though.  If we created a FIFO for FreeBSD then both the
FIFO and its parent directory still need to be removed when we get
notification that the associated asynchronous command has completed.

That said, we can leave the "close fd" parts in situ just in case.
We'll do some mitigation.  Originally I thought to use
``suppress-errors!`` but that applies a host of template and trap code
when in practice we know that most of the time the file descriptor
will have been closed.  So I added a ``libc/close-if-open`` which
reduces it down to a couple of system calls.

However, and somewhat more importantly, FIFOs introduce their own
features as FIFOs are not regular files and have some peculiar
behaviour.

You can experiment with this on FreeBSD although its version of
:manpage:`truss(1)` doesn't tell you which the currently blocked
system call is -- you know, the one you're interested in -- so you
need to read between the lines or force the use of FIFOs on Linux
where :program:`strace` will tell you what system call it is blocked
in.

.. code-block:: console

   $ mkfifo une-pipe
   $ cat une-pipe

Uh, nothing.

It's not even blocked in a read, it is blocked in :manpage:`open(2)`
as:

    When opening a FIFO with O_RDONLY or O_WRONLY set: When opening a
    FIFO with O_RDONLY or O_WRONLY set:

        An *open()* for reading only will block the calling thread
        until a thread opens the file for writing. An *open()* for
        writing only will block the calling thread until a thread
        opens the file for reading.

    --- The Open Group: `open()
     <https://pubs.opengroup.org/onlinepubs/007908799/xsh/open.html>`_

Hmm.  Let's move on and into another window:

.. code-block:: console

   $ echo hello > une-pipe

and our :program:`cat` echoes "hello" to the terminal... and exits.
Wait, what?

Ah, yes.  The act of :program:`echo` *closing* the FIFO has generated
an EOF which is enough for :program:`cat` to quit.

Well, that's not quite true.  The actual behaviour is now more like
:manpage:`pipe(2)` pipes in that once one other thread has opened the
FIFO then the FIFO remains open until all threads with the FIFO open
close it.  So, in other words, you can run

.. code-block:: console

   $ (echo hello; sleep 10; echo world) > une-pipe

in one window, holding the FIFO open for a little over ten seconds and
in (yet) another window run:

.. code-block:: console

   $ echo breaking > une-pipe

and you'll just get "breaking" somewhere in between the "hello" and
"world".  "breaking" does not generate the EOF, it is the number of
threads holding the FIFO open for writing reducing down to zero that
generates the EOF.

Subtle!

This may seem a bit academic but as we're handling the FIFO we need to
be all over this.  If the asynchronous command associated with a FIFO
fails, we need to have an appropriate card up our sleeve.

For example, if, in the preparation for our :program:`echo` command we
were to crash and burn:

.. code-block:: idio

   fn := named-pipe-from {
     libc/exit 9
     echo "hello"
   }

   fh := open-output-file fn

Then the chances are that we will block trying to open the FIFO --
both times.  :socrates:`Eh?` We, the parent, clearly try to open the
FIFO but the asynchronous command, or rather the sub-:lname:`Idio`
launched to run the asynchronous command, tries to open the FIFO
during the prep stage as it tries to make the FIFO its *stdin*.

In principle, then, both processes, us, the parent, and the
sub-:lname:`Idio`, will synchronise and will both be trying to open
the FIFO at the same time and then the operating system will allow us
both to proceed.

The asynchronous command immediately exits with 9 and any subsequent
activity by the parent :lname:`Idio`, notably, :manpage:`read(2)`,
will get an EOF indication.

There's another, slightly more subtle aspect that affects our simple
tests.  Suppose our test is:

.. code-block:: idio

   fn := named-pipe-from {
     cat "/dev/fd/0" > testfile
   }

   fh := open-output-file fn
   puts "hello\n" fh
   close-handle fh

In the parent, we will coordinate our open of the FIFO with the
asynchronous command opening the FIFO for its *stdin* and we'll write
"hello\\n" and be done.

The asynchronous command, however, is likely to be a little slower off
the mark as it does it's prep, figures out the redirection and then
launches :program:`cat`.  That, in itself, isn't the problem.  The
problem is that :program:`cat` sees :file:`/dev/fd/0` as "just another
file" and will *open* it.

If the parent has already written "hello\\n" to the FIFO and closed
the handle then there's no-one with the FIFO open for writing and
:manpage:`read(2)` will block.

*Bah!*

We can start a fix with non-blocking I/O but there are knock-on
effects.

If we tag the pathname we're returning as a FIFO (much like we tagged
pipes for :file:`/dev/fd` systems) then we can know to use O_NONBLOCK.

But, careful, though!  Only the parent wants O_NONBLOCK.  If the
asynchronous command side has O_NONBLOCK set then, with our race
condition hats on, it will get EOF the moment it tries to read,
potentially long before we get round to opening our end of the pipe.
This forces ``proc-subst-named-pipe`` to diverge into
``proc-subst-named-pipe-into`` and ``proc-subst-named-pipe-from``
forms so that the inner code can know whether to tags the read/write
pathnames with the magic O_NONBLOCK flag.

With O_NONBLOCK, the *open* will return immediately however, it is our
future :manpage:`read(2)` that we need to be careful with:

    When attempting to read from an empty pipe or FIFO:

    * If no process has the pipe open for writing, *read()* will
      return 0 to indicate end-of-file.

    * If some process has the pipe open for writing and O_NONBLOCK is
      set, *read()* will return -1 and set errno to [EAGAIN].

    --- The Open Group: `read()
     <https://pubs.opengroup.org/onlinepubs/007908799/xsh/read.html>`_

and :manpage:`write(2)` is even more complicated:

    If the O_NONBLOCK flag is set, *write()* requests will be handled
    differently, in the following ways:

    * The *write()* function will not block the thread.

    * A write request for {PIPE_BUF} or fewer bytes will have the
      following effect: If there is sufficient space available in the
      pipe, *write()* will transfer all the data and return the number
      of bytes requested. Otherwise, *write()* will transfer no data
      and return -1 with errno set to [EAGAIN].

    * A write request for more than {PIPE_BUF} bytes will case one of
      the following:

      * When at least one byte can be written, transfer what it can
        and return the number of bytes written. When all data
        previously written to the pipe is read, it will transfer at
        least {PIPE_BUF} bytes.

      * When no data can be written, transfer no data and return -1
        with errno set to [EAGAIN].

    --- The Open Group: `write()
     <https://pubs.opengroup.org/onlinepubs/007908799/xsh/write.html>`_

*<sigh>* Just for completeness, then:

    If the O_NONBLOCK flag is set, or if there are any pending
    signals, *close()* does not wait for output to drain, and
    dismantles the STREAM immediately.

    --- The Open Group: `close()
     <https://pubs.opengroup.org/onlinepubs/007908799/xsh/close.html>`_

That's all too complicated for us (read: me!) right now.  There's a
reason why programming languages triumphantly announce their "Async
I/O" package some time down the line.  Asynchronous I/O is hard and
requires some fiddly exactness and therefore some fiddlingly exact
thinking.

.. aside::

   And prep the big announcement!

Let's come back to that.

In the meanwhile.  Don't use "named pipes" in :lname:`Idio` code just
use regular pipes!

Tidying Up Process Substitution
===============================

What do we do about tidying up?  *When* do we do tidying up?

We will have created an entry in ``%%process-substitution-jobs`` when
we created the asynchronous command, a map of *job* to a
``%process-substitution-job`` struct.

``tidy-process-substitution-job`` will get invoked when the *job*
completes -- which includes when it errors.

/dev/fd/
--------

Suppose we were reading from a pipe and the asynchronous command
completes normally.  We **should not** pro-actively close the pipe as
the writer will have left some data in the pipe and we, the reader,
should be able to retrieve it normally and, having read all the stored
data, get an EOF.

What happens if the asynchronous command failed in some way?  We may
or may not get a warning -- depending on the value of
``suppress-async-command-report!`` -- but what should we do about the
pipe?

Clearly, we have two choices.  We could do nothing and have the reader
read whatever the asynchronous command had gotten round to writing
into the pipe and then get an EOF.  It would be none-the-wiser that
the pipe had failed though.

Alternatively, we could pro-actively close the pipe, under the feet of
the reader (us!), and subsequent operations will get EBADF.
(Hopefully!)

I think I prefer the later.  Something went wrong and the user should
get to know because we started throwing errors everywhere.

Do we need some means of suppressing this behaviour, though?  Maybe
the writer is a known ropey program.

What if we were writing to the pipe?  Of interest, can the
asynchronous command exit successfully while we're still writing?
``head -1`` suggests that it can so we need to consider our options.

If there's any kind of error, we should let the user know by closing
the pipe under their feet.

If there was no error, the ``head -1`` example, I still think we
should close the pipe under the writer's feet.  It seems to me to be
the right thing to do, however inconvenient.

You fancy that this might be a more popular candidate for suppression!

FIFOs
-----

FIFOs are more interesting again as they are entries in the file
system which we need to remove.  We can do that in a similar way to
closing the file descriptor for :file:`/dev/fd` systems when the
asynchronous command completes.

However, we don't have a handle *[sic]* on the file handle the user is
using to access the FIFO.  In other words we have no control other
than to remove the FIFO from the file system before the user opens it
-- in all likelihood, a very small window.

That said, if the user hadn't opened the FIFO before we removed it
then they'll get an ``^i/o-no-such-file-error`` (ENOENT).  If they had
already opened the FIFO then... I don't know.

Something to come back to.

.. include:: ../../commit.rst


.. include:: ../../global.rst

.. _`process substitution`:

********************
Process Substitution
********************

Rather than the similarly named *Command Substitution*, where we want
to substitute the collected output of a command, with *Process
Substitution* we want to substitute a filename for another command to
use.

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

In the first instance, it would be nice to use the :file:`/dev/fd/N`
format as it clearly represents what it is and has the nice advantage
that the operating system maintains it.

.. sidebox::

   Clearly, there will be some operating system process-indirection
   involved as we can't be having people poking each others'
   :file:`/dev/fd/0` file descriptors.

In essence, if we create a :manpage:`pipe(2)` for inter-process
communication then each of the pipe's file descriptors will have a
:file:`/dev/fd/N` entry associated with it.  

For those systems that don't support :file:`/dev/fd` then we'll have
to create a named pipe and use its name instead.

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

First up, FreeBSD doesn't use the :file:`/dev/fd/` form.  Well,
careful, it *does* for file descriptors 0, 1 and 2 but not for
anything else.  :lname:`Bash` figures this out with a judicious ``exec
test -r /dev/fd/3 3</dev/null`` in :file:`aclocal.m4`.  On the plus
side, it is a pipe.

Of the operating systems that do support :file:`/dev/fd` you'll notice
they are all using file descriptor 63.  That's because :lname:`Bash`
chooses to:

    Move the parent end of the pipe to some high file descriptor, to
    avoid clashes with FDs used by the script.

I guess that defers the problem with users having to guess which file
descriptors are free when they want to stash a file descriptor, as in
``exec >&3``, and generally just plumping for a low numbered one, as
in 3.  Too bad if that was important.

SunOS is a bit more interesting, :file:`/dev/fd/63` is a character
special device (and owned by *root*).  In fact, many (all possible?)
:file:`/dev/fd/N` exist.  I guess you're meant to know your own file
descriptors.

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

However, with a ``named-pipe-from`` we intend that *another*
sub-program utilise this name (although, there's no reason why *we*
shouldn't use it -- that depends on what the code says).

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

We can close our reader end of the named pipe when the sub-process
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
      /tmp//sh-np.TixduF

   (Technically, you will have gotten your prompt back so that should
   read ``$ /tmp//sh-np.TixduF``.)

   Here we are backgrounding the Group Command meaning that
   :program:`bash`, as in ``bash -c``, will exit leaving the
   backgrounded process, another :program:`bash`, running.

   Notice, given that the named pipe remains, that the sub-shell
   :program:`bash` is not the one tracking ``fifo_list`` so it isn't
   removed -- or there is a *exit_shell()* race condition!

   Look out for directories called :samp:`sh-np.{xxxxxx}` from
   :lname:`Bash` or :samp:`idio-np-{xxxxxx}` from :lname:`Idio` in
   :envvar:`TMPDIR` or :file:`/tmp` or wherever.



.. include:: ../../commit.rst


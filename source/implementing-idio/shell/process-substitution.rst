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

If you were to give :program:`cat` the contents of :file:`file` then
it won't be very happy.

External commands are not the only use, I frequently use process
substitution in loops:

.. code-block:: bash

   while read line ; do
       ...
   done <(cat file)

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

#. we have to recognise the command we are going to run for process
   substitution

#. we need to run it

#. we need to marry this up with a (possibly named) pipe

(Named) Pipes
=============

You would think this would be the easy bit but oh, no!

In the first instance, it would be nice to use the :file:`/dev/fd/N`
format as it clearly represents what it is and have the nice advantage
that the operating system maintains it.

.. sidebox::

   Clearly, there will be some operating system process-indirection
   involved as we don't want people nosing at each others'
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

   Linux  $ ls -l <(sleep 1)
   lr-x------. 1 idf   idf        64 Jun 11 12:14 /dev/fd/63 -> 'pipe:[1781424]'

   SunOS  $ ls -l <(sleep 1)
   crw-rw-rw-  1 root  root  578, 63 Jun 11 12:15 /dev/fd/63

   Mac OS $ ls -l <(sleep 1)
   prw-rw----  0 idf   staff       0 11 Jun 12:16 /dev/fd/63

   FreeBSD$ ls -l <(sleep 1)
   prw-------  1 idf   wheel       0 Jun 11 12:17 /tmp//sh-np.OrAlUF

Hmm.  There's a few things to digest there.

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
descriptors are free and generally just plumping for a low numbered
one.

SunOS is a bit more interesting, :file:`/dev/fd/63` is a character
special device (and owned by *root*).  In fact, many (all possible?)
:file:`/dev/fd/N` exist.  I guess you're meant to know your own file
descriptors.

Mac OS is possibly the most honest in that :file:`/dev/fd/63` is a
(named) pipe.

Linux has :file:`/dev/fd/63` be a symlink to what we presume must be a
pipe.  ``ls -lL`` confirms that.

Running
=======

Running the command, married up to a (named) pipe should have the
heavy work done already.  We have ``pipe-into`` and ``pipe-from``
mechanisms from the *Command Substitution* work so, presumably, we can
re-use that.

The trickier bit is arranging the pipe's name.  Well, the *name*
should be easy enough but I mean having established a ``pipe-from``
sub-command then *we* would normally use the read end of the pipe.

Nominally, we intend that *another* sub-program utilise this name --
although, there's no reason why *we* shouldn't use it.  That depends
on what the code says.

If we want a sub-program to use this (named) pipe then we should
ensure that we don't set ``FD_CLOEXEC`` on the file descriptor --
otherwise it'll be a short-lived exercise.  This is different to a
regular pipeline where we would have :manpage:`dup2(2)`'d the file
descriptor to ``STDIN_FILENO`` or ``STDOUT_FILENO`` and set
``FD_CLOEXEC`` on the original :manpage:`pipe(2)` file descriptor.

Of course, if we do run a sub-program then we, the parent, should
close our copy of the fie descriptor -- otherwise it'll hang around --
but if the code is going to use the result in the original process
then we shouldn't.

I suppose the difference is between:

.. code-block:: idio-console

   Idio> ls -l <(/usr/bin/sleep 1)

where *we* won't be using :file:`/dev/fd/N` but the sub-program
:program:`ls` will.  We should :manpage:`close(2)` it but not set
``FD_CLOEXEC`` for :program:`ls`.

On the other hand:

.. code-block:: idio-console

   Idio> open-input-file <(/usr/bin/sleep 1)

means *we* are going to use the (named) pipe so shouldn't be closing
it.

Yuk!



.. include:: ../../commit.rst


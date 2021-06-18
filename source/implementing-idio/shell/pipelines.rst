.. include:: ../../global.rst

.. _`pipelines and IO`:

*****************************
Pipelines and I/O Redirection
*****************************

It's worth a few words to describe the straight-forward task of
implementing pipelines (hint: it's not that straight-forward) and I/O
redirection (not that straight-forward either).

\| Operator
===========

In the first instance, the ``|`` operator doesn't behave like most
other reader operators which "simply" re-arrange the elements of a
list with a view to calling a different but related function with the
results.

For reasons almost certainly involving unchecked enthusiasm and
limited self-control, the ``|`` operator does the whole pipeline
malarkey itself.  I suppose, *technically*, you could regard that as
simply re-arranging all the elements of the origin list in the reader
but it's a little bit more than that.

It's all defined in :file:`lib/job-control.idio` (with duplicating
efforts in :file:`src/job-control.c` as I wrote it first and some of
it is still used) and mostly from the directions in the
:program:`info` pages on *Job Control* (in *libc* or read the `online
JOb Control`_ pages) but there's a few twists and turns.

I'm going to assume that we're all happy with the basics of running a
sub-program in the context of job control which involves prepping a
process' I/O and fiddling with the controlling terminal and foreground
job.

.. aside::

   It's not like *I* know what I'm doing, I'm just following the other
   guy.

That's a given, right?  If not, read the :program:`info` pages,
realise that's there's nothing too surprising other than how
straight-forward it is and then read the code for ``fork-command`` in
:file:`lib/job-control.info` and find it's all reasonably one-for-one.

That's for a simple foreground or background command.  When it comes
to pipelines there is a long row and a lot of ducks.

pgrp-pipe
---------

There's a little process coordination trickery ported from
:lname:`Bash` -- noting that if the race condition occurs in a slick
and fast pure :lname:`C` environment then our meandering and
inefficient byte-compiled script has no hope!

We need to prevent the first process in the pipeline from starting
until all the others are in place -- otherwise you can have the first
process, the process group leader, run and exit before you manage to
start any of the others!  That also leaves the small issue of trying
to call :manpage:`setpgid(2)` with a process group that no longer
exists (and, worse, could have been replaced with a different process
all together).  That's all bad for business.

The trick is to open *another* pipe and have the first process block
reading from the pipe just before it starts.  All the other processes
in the pipeline simply close the pipe when they're about to
exec/start.  When the last one has closed the pipe the first will have
its blocking :manpage:`read(2)` return (with zero bytes, ie EOF -- we
don't care) and we're good to go.

Incidentally, as we created the pipe in the main Idio process, it too
holds the pipe open so we can be fairly confident that all the child
processes are set up and running when the main Idio process closes the
(last?) ``pgrp-pipe`` write-end.

Well, probably, there's always a race condition between closing the
``pgrp-pipe`` and :manpage:`execve(2)`\ ing or starting processing the
:lname:`Idio` code in which the last process can be prevented from
running before all the previous processes have been and gone.  But
we've done a decent job, what more can we do?


Pipeline Bookkeeping
--------------------

Most of the work in a pipeline is done with file descriptors whereas
the caller is dealing with handles.

.. sidebox::

   This is a reader operator, ie. a template and so our "variables"
   will be unquoted entities to keep the pipeline as hygienic as
   possible.  Essentially, everything will have a ``$`` in front of
   it when the action starts.

There is an overall ``$pipeline-r-fd`` and ``$pipeline-w-fd`` -- which
the first and last commands use (indirectly via the per-command
``$cmd-r-fd`` and ``$cmd-w-fd``).

``$cmd-pipe`` is the inter-cmd pipe, created by the left hand command to
generate its own output file descriptor and then to leave trailing
around the loop an input file descriptor for the next command.

For each command there is a per-cmd input file descriptor,
``$cmd-r-fd``, and output file descriptor, ``$cmd-w-fd``.

The ``$cmd-r-fd`` is normally the pipe-reader of the previous
command's ``$cmd-pipe`` except, of course, the first command whose
``$cmd-r-fd`` is ``$pipeline-r-fd``.

The ``$cmd-w-fd`` is normally the pipe-writer of of ``$cmd-pipe``
except, of course, the last command whose ``$cmd-w-fd`` is
``$pipeline-w-fd``.

The ``$pipeline-*-fd``, the overarching input and output of the entire
pipeline, could be:

#. entities figured out by ``(stdin-fileno)`` and ``(stdout-fileno)``,
   ie.:

   * regular :lname:`C` ``STDIN_FILENO`` and ``STDOUT_FILENO``

   * whatever ``(current-input-handle)`` and
     ``(current-output-handle)`` actually are

   * either of which which could be string-handles (necessitating
     temporary files and some post-pipeline content recovery)

#. actual pipes!

#. future *stuff* (sockets are the obvious missing contender)

Meta-Commands
-------------

We can extend this model with some meta-commands, that is we can
prefix the pipeline with a symbol to indicate some more bespoke
behaviour is required.

Prefixing the pipeline continues an overall style of :samp:`{cmd}
{args}`. where, in this case, :samp:`{args}` happens to be an entire
pipeline.

You can only use a single meta-command per pipeline.

fg-job / bg-job
^^^^^^^^^^^^^^^

``'fg-job`` is the default behaviour and is added for completeness.

``'bg-job`` will run the pipeline in the background.  Obviously, if
the pipeline reads from its *stdin* or writes to its *stdout* while
backgrounded then the process group will get an appropriate signal,
``SIGTTIN`` or ``SIGTTOU``, respectively.

.. note::

   These are not like, say, :lname:`Bash`'s ``fg`` and ``bg`` commands
   which look at the set of outstanding jobs and run the targeted one
   in the foreground or background.

pipe-into / pipe-from
^^^^^^^^^^^^^^^^^^^^^

If the caller passed ``'pipe-into`` or ``'pipe-from`` as the first
argument of the pipeline then ``$pipeline-*-fd`` will be real pipes
and the other ends of these are returned as pipe handles,
``$pipeline-w-ph`` and ``$pipeline-r-ph``, for the caller to write
into and read from the pipeline.

In practice, a ``$use-w-pipe`` or ``$use-r-pipe`` flag is set and we
set ``$pipeline-*-fd`` to the appropriate end of a :manpage:`pipe(2)`
and prepping ``$pipeline-*-ph`` to a pipe handle of the other end to
be returned to the caller.

collect-output
^^^^^^^^^^^^^^

This is *Command Substitution* in that we'll set ``$pipeline-w-fd`` to
a temporary file to collect the output.  We'll use
``libc/make-tmp-fd`` which removes the temporary file name before
returning the file descriptor.

When we're done with the pipeline, we'll slurp the contents of the
temporary file back into a string handle then return the string
contents of the string handle back to the caller.

Simple Commands
---------------

Reducing the pipeline down to its simplest case causes us a problem.
Consider:

.. code-block:: idio-console

   Idio> pipe-from cat file

There is no ``|`` symbol so no ``|`` reader operator gets invoked.  We
will now try to find and execute the external command ``pipe-from``
which will probably(!) fail.

To this end we need to rustle up some single-instance meta-commands:
``fg-job``, ``bg-job``, ``pipe-into``, ``pipe-from`` and
``collect-output`` most of which are wrappers to a generic
``fork-command`` which runs job control much like the main pipeline
operator does.

``collect-output`` is slightly different in that it runs a combination
of ``with-output-to`` (a variation on ``with-handle-redir``, below)
and ``fg-job`` to force the command into a sub-program.

Exiting
=======

With our book keeping hats on we do have a minor problem when we exit
in that there could be un-waited for jobs lying around.  This is
particularly prevalent if they were run immediately before we exit.

What should we do with them?  The info pages skip over this but we can
take a look at what :lname:`Bash` does which is to terminate all
stopped jobs: you can follow *exit_shell()* in :file:`shell.c` to
*end_job_control()* in :file:`jobs.c` to *terminate_stopped_jobs()*.

Of course that means that any backgrounded not-stopped jobs continue.

HUPing
======

In a similar vein, if we are sent a SIGHUP signal then we should pass
it onto to all of our jobs and then quit.

I/O Redirection
===============

Our problem with I/O redirection isn't the redirection, mostly, but
that we don't, in general, use file descriptors.  In fact, we happily
deal with string handles which don't have any file component
whatsoever.

Note that:

* this only works for the standard I/O stream, *stdin*, *stdout* and
  *stderr*

  The underlying problem being that I didn't want to deal with, say,
  :lname:`Bash`'s arbitrary redirection syntax, :samp:`[n]>[word]`,
  which has too much ambiguity for the :lname:`Idio` reader.

* only works *after* the command and arguments, as in ``ls -l > osh``

  Again, :lname:`Bash`'s syntax is too flexible (for me).

We have two forms of I/O redirection:

#. actual I/O redirection, as in ``>``, which we deal with in ``with-handle-redir``

#. I/O duplication, as in ``>&``, which we deal with in ``with-handle-dup``

.. aside::

   The nearest I've gotten recently was to reformat the text...

These two should probably be merged via some clever coding.

with-handle-redir
-----------------

The actual I/O redirection operators, ``<``, ``>`` and ``2>``,
determine that they affect a *type* of ``'input``, ``'output`` or
``'error`` and take the first expression after as the target.

They then package the command before the redirection statement in the
form of a thunk and pass it to ``with-handle-redir`` with the type and
target arguments.

``with-handle-redir`` then defines a bunch of accessor methods based
on the type and then look at the target:

* if target is the correct direction (input or output!) file
  descriptor handle then we can use it

  Note that all file handles are (by definition?) file descriptor
  handles.

  This also covers pipe handles which are also file descriptor
  handles.

* otherwise if target is a file descriptor handle then it must be in
  error (as it should have passed in the previous test)

* if target is the correct direction (input or output!) string handle
  then we can use it

* otherwise if target is a string handle then it must be in error (as
  it should have passed in the previous test)

* if target is a string then it is deemed a filename and opened (for
  input or output)

* if target is ``#n`` then it is a nickname for "/dev/null" which is
  opened (for input or output)

* otherwise, target is an invalid value

Assuming we still going then we set the appropriate handle
(``set-input-handle!``, ``set-output-handle!`` or
``set-error-handle!``) and run the thunk.

Finally, set the handle back.

with-handle-dup
-----------------

The actual I/O redirection operators, ``<&``, ``>&`` and ``2>&``,
determine that they affect a *type* of ``'input``, ``'output`` or
``'error`` and take the first expression after as the target.

They then package the command before the redirection statement in the
form of a thunk and pass it to ``with-handle-dup`` with the type and
target arguments.

``with-handle-dup`` then defines a bunch of accessor methods based
on the type and then look at the target:

* if target is the correct direction (input or output!) file
  descriptor handle then we can use it

  Note that all file handles are (by definition?) file descriptor
  handles.

  This also covers pipe handles which are also file descriptor
  handles.

* otherwise if target is a file descriptor handle then it must be in
  error (as it should have passed in the previous test)

* if target is the correct direction (input or output!) string handle
  then we can use it

* otherwise if target is a string handle then it must be in error (as
  it should have passed in the previous test)

* if target is a ``C/int`` or fixnum with a value of 0, 1 or 2 then
  the current input, output or error handle is used as the target
  handle

* otherwise, target is an invalid value

Assuming we still going then we set the appropriate handle
(``set-input-handle!``, ``set-output-handle!`` or
``set-error-handle!``) and run the thunk.

Finally, set the handle back.

.. include:: ../../commit.rst


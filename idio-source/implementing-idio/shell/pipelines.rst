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
Job Control`_ pages) but there's a few twists and turns.

I'm going to assume that we're all happy with the basics of running a
sub-program in the context of job control which involves prepping a
process' I/O and fiddling with the controlling terminal and foreground
job.

.. aside::

   It's not like *I* know what I'm doing, I'm just following the other
   guy.

.. aside::

   Well, imagine it *was* all reasonably one-for-one until someone
   came along and started "adding value."  We all know how that ends
   up.

That's a given, right?  If not, read the :program:`info` pages,
realise that's there's nothing too surprising other than how
straight-forward it is and then read the code for ``fork-command`` in
:file:`lib/job-control.info` and find it's all reasonably one-for-one.

That's for a simple foreground or background command.  When it comes
to pipelines there is a long row and a lot of ducks.

Processes
---------

There's more than meets the eye, here.

From the perspective of the pipeline generating code, being a
template, it doesn't know what the meaning of any of the sub-processes
are:

.. parsed-literal::

   rhubarb rhubarb | custard custard

It doesn't know if any of that is non-external command :lname:`Idio`
code, say, ``printf``, or is an actual external command, say,
``echo``, or a block of code that mixes external and non-external
commands together.  It's just *stuff*.

All that the pipeline operator can do is arrange for the whole
"sub-process joined with a pipe to sub-process" malarkey to be set up
and have the appropriate sub-process command expanded in situ.

The only extra we're going to add is that after the expansion of the
command we'll add an ``exit 0`` otherwise the sub-process will carry
on running what the main process was about to do.  That's will get
messy very quickly!

* generate pipe 1

* fork 1

  * child process 1

    * input inherited from parent

    * output into pipe 1

    * expand command, ``rhubard rhubard``

    * add ``exit 0``

* fork 2

  * child process 2

    * input from pipe 1

    * output inherited from parent

    * expand command, ``custard custard``

    * add ``exit 0``

As all of that was codified in a template then when it is run the
actual sub-process commands, ``rhubard rhubard`` and ``custard
custard``, will each appear in their own child process with their I/O
redirected through a joining :manpage:`pipe(2)`.

Commands
^^^^^^^^

What if ``rhubard rhubard`` or ``custard custard`` was an external
command or a block that included an external command?

Here, when the VM sees a symbol (or string) in functional position it
will call on the :lname:`C` code to run a child process, just as if
you had typed ``ls -l`` at the command prompt.

The only difference is that this child process is a child of one of
the child processes of the pipeline.  Sub-process 1.1 or 2.1, say.

exit-on-error
^^^^^^^^^^^^^

All of the above is good apart from handling errors.  If, say,
``rhubard rhubard`` was an external command then if it fails we really
want the left hand side of the *pipeline* to fail (preferably in the
same way) even though the process that has failed is a *child* of one
of the sub-processes of the pipeline.

Hence we have the exit-on-error mechanism whereby the default
behaviour is for :lname:`Idio` to exit in the same that the errant
sub-process did.

So, if ``rhubard rhubard`` exits non-zero, or is killed, then we want
child process 1 to react to that by exiting in the same way.

Winding back upwards, if child process 1, of the *pipeline*, exits
non-zero, or is killed, then the parent :lname:`Idio` process, the one
that launched the pipeline through a template, will be signalled and
it can handle the situation appropriately.

If ``rhubard rhubard`` runs normally to completion and exits zero then
we'll hit the deliberately added ``exit 0`` statement which stops the
child process continuing back into the main code and, of course, means
that the parent :lname:`Idio` process, that launched the pipeline,
will see the left hand side exit zero and all is well.

There'll be a small qualification, here, when we have to handle
:ref:`logical expressions <logical expressions>`.

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
the first and last commands use (indirectly via the per-command input
and output file descriptors ``$cmd-r-fd`` and ``$cmd-w-fd``).

``$cmd-pipe`` is the inter-cmd pipe, created by the left hand command
to generate its own output file descriptor, ``$cmd-w-fd``, and then to
leave trailing around the loop an input file descriptor,
``$cmd-r-fd``, for the next command in the pipeline.

The ``$cmd-r-fd`` is normally the pipe-reader of the previous
command's ``$cmd-pipe`` except, of course, the first command whose
``$cmd-r-fd`` is ``$pipeline-r-fd``.

The ``$cmd-w-fd`` is normally the pipe-writer of of ``$cmd-pipe``
except, of course, the last command whose ``$cmd-w-fd`` is
``$pipeline-w-fd``.

The ``$pipeline-[rw]-fd``, the overarching input and output file
descriptors of the entire pipeline, could be:

#. entities figured out by ``(stdin-fileno)`` and ``(stdout-fileno)``,
   ie.:

   * regular :lname:`C` ``STDIN_FILENO`` and ``STDOUT_FILENO``

   * whatever ``(current-input-handle)`` and
     ``(current-output-handle)`` actually are

     * either of which which could be string-handles (necessitating
       temporary files and some post-pipeline content recovery)

#. actual pipes!

#. future *stuff* (sockets are the obvious missing contender)

.. _`pipeline meta-commands`:

Meta-Commands
-------------

We can extend this model with some meta-commands, that is we can
prefix the pipeline with a symbol to indicate some more bespoke
behaviour is required.

Prefixing the pipeline continues an overall style of :samp:`{cmd}
{args}`. where, in this case, :samp:`{args}` happens to be an entire
pipeline.

You can use a number of meta-commands per pipeline although some
conflict.  The effectiveness depends on which is checked for first
after the pipeline is successfully launched.

You have a similar concept to meta-commands in :lname:`Bash` in that a
pipeline can be preceded by ``time [-p]``.

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

   ``bg-job`` is more closely aligned with the function of the shell's
   ``&`` operator, as in:

   .. code-block:: bash

      cmd args &

   where in :lname:`Idio` you might write:

   .. code-block:: idio

      bg-job cmd args

pipe-into / pipe-from
^^^^^^^^^^^^^^^^^^^^^

If the caller passed ``'pipe-into`` or ``'pipe-from`` as the first
argument of the pipeline then ``$pipeline-r-fd`` or ``$pipeline-w-fd``
will be real pipes and the other ends of these are returned as pipe
handles, ``$pipeline-w-phn`` or ``$pipeline-r-phn``, for the caller to
write into and read from the pipeline.

In practice, a ``$use-w-pipe`` or ``$use-r-pipe`` flag is set and we
set ``$pipeline-[rw]-fd`` to the appropriate end of a
:manpage:`pipe(2)` and assigning ``$pipeline-[wr]-phn`` to a pipe
handle constructed from the other end to be returned to the caller.

These two meta-commands set the :ref:`asynchronous command
<asynchronous commands>` flag on the job.

As reasonable analogy would be something like ``"|cmd args"`` or
``"cmd args|"`` in :lname:`Perl`.  The second case is anathema to us
as the syntactic distinguisher, the ``|"``, is at the end of the
expression.  That breaks our *cmd args* model.

I don't have a particularly good answer for that.  Maybe we need the
reader to support:

.. csv-table::
   :widths: auto

   ``|``, a regular pipe
   ``|>{...}`` ``|>(...)``, syntactic sugar for ``pipe-into``
   ``|<{...}`` ``|<(...)``, syntactic sugar for ``pipe-from``
   ``||``, *reserved*

named-pipe-into / named-pipe-from
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the caller passed ``'named-pipe-into`` or ``'named-pipe-from`` as
the first argument of the pipeline then ``$pipeline-r-fd`` or
``$pipeline-w-fd`` will be real pipes and the other ends of these are
returned as *pathnames*, ``$pipeline-w-phn`` or ``$pipeline-r-phn``,
for the caller to open and write into and read from the pipeline.

In practice, the same ``$use-w-pipe`` or ``$use-r-pipe`` flag is set
to ``'named`` and we figure out a system dependent pathname to return.
See the section on :ref:`Process Substitution` for more details.

These two meta-commands set the :ref:`asynchronous command
<asynchronous commands>` flag on the job.

Following the above reader forms, perhaps:

.. csv-table::
   :widths: auto

   ``>{...}`` ``>(...)``, syntactic sugar for ``named-pipe-into``
   ``<{...}`` ``<(...)``, syntactic sugar for ``named-pipe-from``

These reader forms clearly only differ by a leading ``|`` symbol from
their non-*named* variants.  Not much.

.. aside::

   I see that we `SVO speakers
   <https://en.wikipedia.org/wiki/Subject%E2%80%93verb%E2%80%93object>`_
   are not in the majority.  So I apologise for my assumptions about
   how easily some constructions may scan.  I'm not about to change my
   mind, though.

   Not for *that* reason, anyway.

I don't feel too bad about that, though.  This form, the *named* form,
implementing *Process Substitution*, is clearly a match for the
:lname:`Bash`-style for *Process Substitution*.  The non-*named*
variant has a visual mnemonic: ``|>``, I feel, says *pipe into*.

.. _`collect-output`:

collect-output
^^^^^^^^^^^^^^

This is *Command Substitution* in that we'll set ``$pipeline-w-fd`` to
a temporary file to collect the output.  We'll use
``libc/make-tmp-fd`` which calls :manpage:`mkstemp(3)` and removes the
temporary file name before returning the file descriptor.

When we're done with the pipeline, we'll slurp the contents of the
temporary file back into a string handle then return the string
contents of the string handle back to the caller.

``collect-output`` is always run as a foreground command -- we're
waiting for the results before we can continue, after all!

This meta-command sets the :ref:`asynchronous command <asynchronous
commands>` flag on the job.

time
^^^^

All jobs have start and end statistics recorded including
:manpage:`gettimeofday(2)` and :manpage:`getrusage(2)` for "self" and
"children".

The ``time`` meta-command sets a ``report-timing`` flag which is
tested by ``wait-for-job`` which can report much like :lname:`Bash`'s
``time`` prefix.

.. aside::

   I *think* this helps me subconsciously get a feel for how long
   things should take and therefore raise a subconscious alert that
   things aren't quite going right.

   Or I have an undiagnosed psychological disorder.  Which is fine.
   Timing things doesn't hurt anyone, right?

   (You're taking a long time to answer that...)

I use ``time`` in :lname:`Bash` all the, er, time although it wasn't
until I added this meta-command that I came to realise that it's not
all it's cracked up to be.

The problem is that :manpage:`getrusage(2)`'s ``RUSAGE_CHILDREN``
represents all descendent processes that have terminated and been
waited on.  (It does not include any not yet terminated and waited on
descendents.)

So, here at least, we assume it was the job we just ran but maybe it
was also the other jobs that just finished and ``wait-for-job`` has
run for off the back of a ``SIGCHLD``:

    Return resource usage statistics for all children of the calling
    process that have terminated and been waited for.

    --- :manpage:`getrusage(2)`

*We're* the calling process and we've *lots* of children.  Hmm.

I dunno.  I guess if you're pretty confident that you only had one
thing running (and now completed) then this usage is probably fairly
accurate.

If you'd fired off a dozen jobs in the background that completed
whilst this job was running then you can be less confident (as can
``wait-for-job`` if it is reporting on those jobs).

On the plus side, ``tv-real`` (the elapsed real time) should be
accurate.  Erm, except that the *end* time is dependent on when
``wait-for-job`` wakes up.

So, use it as a hand-wavy, *about this much* time.

Meta-Command Preferences
^^^^^^^^^^^^^^^^^^^^^^^^

The meta-commands are utilised in the following order (in order words,
if you have set two conflicting meta-commands then the first listed is
used):

#. ``named-pipe-into``

   returning a pathname

#. ``pipe-into``

   returning an output pipe handle

#. ``named-pipe-from``

   returning a pathname

#. ``pipe-from``

   returning an input pipe handle

#. ``collect-from``

   which always runs the job in the foreground

   returning the :ref:`stripped <strip-string>` collected output
   discarding trailing newlines, U+000A (LINE FEED)

#. ``fg-job``

   returning the job status (``#t`` or ``#f``)

#. ``bg-job``

   returning ``#t``

Further Meta-Commands
^^^^^^^^^^^^^^^^^^^^^

With these sorts of options to hand we can start to imagine some more
exotic forms.

Suppose we wanted to return a named-pipe pathname to a command and yet
retain control over what is written by also getting the other end of
the pipe returned to us?

You can imagine a sort of:

.. code-block:: bash

   diff file <( ... )

where, instead of ``...`` being an asynchronous command, *we* somehow
get an output pipe handle to give :program:`diff` some input through
the named pipe of that second argument.

Well, we can't return two things and certainly not to two different
people but maybe there's a trick we can pull?

Suppose we passed a function expecting a single argument (the putative
output pipe handle) as ``...``?  Under those circumstances, the code
could detect that the value passed was a function and call it with the
appropriate end of the pipe.

The function would be expected to assign the value to a variable in
scope, a trick with "private variables" we've played before.

The meta-command code can continue on and return the named pipe as an
argument to the command as it would have done normally.

At this point however, we get a disturbance in the force.
:program:`diff` wants to run in the foreground reading from
:file:`/dev/fd/{X}` or whatever as it would have done normally and
*we* now want to run in the foreground in order to supply
:program:`diff` with some input.

.. aside::

   And perhaps :program:`diff` wasn't the best example.

One or other is going to have to be run the in the background which is
going to be problematic if whichever wants to write to the terminal.
Let's go with the command being run in the background -- a complete
*volte-face* from previous behaviour -- but we are doing something
exotic!

You can imagine something like:

.. code-block:: idio

   oph := #f

   define (set-oph ph) {
     oph = ph
   }

   diff file <( set-opf )

   hprintf oph "hello\n"

   close-handle oph

Now we have to wait for and get the exit status of :program:`diff` --
assuming it hasn't been stopped for trying to write to the terminal.

This mechanism is not too far fetched from the various "Coprocess"
facilities from newer :lname:`Bash`'s and :lname:`Ksh` although we are
retaining a connection with a specific argument in the command's
arguments.

Coprocesses themselves should be equally feasible.

Asynchronous Command House-Keeping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's a tiny bit more annoyance with asynchronous commands, in
particular with the pipe we create to pass data into or out of the
asynchronous command.

This is going to get messy so let's take an example and work it
through:

.. code-block:: idio

   oph := pipe-into {
     cat > file
     do something else
   }

We obviously create the connectivity pipe in the parent :lname:`Idio`
as it is that parent which is going to utilise the pipe (even if that
is just giving the pipe (handle or name) to someone else, it, the
parent, needs the one end).  Here, the parent wants the *write end* of
the connectivity pipe and will return an output pipe handle for the
user to write into.

We now :manpage:`fork(2)` a sub-:lname:`Idio` to run through the
asynchronous command itself.  It will dutifully remap its own *stdin*
or *stdout* according to the asynchronous connectivity and close the
corresponding read or write end of the pipe.  So, here, the
sub-:lname:`Idio` will :manpage:`dup2(2)` the *read end* of the
connectivity pipe to *stdin* for the asynchronous commands and will
:manpage:`close(2)` the original connectivity pipe file descriptor
(10, or whatever, who cares?).

We now run the asynchronous commands.  :program:`cat` will read its
*stdin* and print the contents to *stdout* which we happen to have
redirected to :file:`file`.

But wait, :program:`cat` hangs.  What's going on?  Well,
:program:`cat` reads from its *stdin* until it gets an *EOF*.  If we
:program:`strace` it we see it happily blocked reading from file
descriptor 0.  "ENOEOF" -- if we could make up new error codes.

The problem, here, is that :program:`cat`'s *stdin* is a pipe and the
problem with pipes is that they remain open, without an EOF indicator,
whilst anyone still holds a *write end* open.

That's where we've made our mistake.  The parent :lname:`Idio` has the
write end open -- otherwise we're not going to do much "piping into"
-- and then we *forked*.  The sub-:lname:`Idio` *also* has the write
end open.  In fact, if you nose around carefully, :program:`cat` has
the write end open too as it was forked from the sub-:lname:`Idio`.
*D'oh!*

So, our extra bit of house-keeping for asynchronous commands is to
ensure that the sub-:lname:`Idio` closes down the other end of the
connectivity pipe from the one it needs.  Or, another way of
describing it, is that the sub-:lname:`Idio` needs to close the end of
the connectivity pipe that the parent :lname:`Idio` will be keeping
open.

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
in that there could be jobs lying around for which we haven't called
:manpage:`wait(2)`.  This is particularly prevalent if they were run
immediately before we exit.

What should we do with them?  The info pages skip over this but we can
take a look at what :lname:`Bash` does which is to terminate all
stopped jobs: you can follow *exit_shell()* in :file:`shell.c` to
*end_job_control()* in :file:`jobs.c` to *terminate_stopped_jobs()*.

Of course that means that any backgrounded not-stopped jobs continue.

    .. aside::

       It felt like the old `Alexei Sayle
       <http://www.alexeisayle.me/>`_ gag where he notes that the
       capacity of the mind is finite and when you're walking down the
       street and someone tells you a new fact you forget how to walk.

    When I typed that, I'll be honest, I had a mental panic thinking,
    "What a *disaster*\ !  Are we not in control?" as I'd not thought
    about the functionality using that expression and `couldn't see
    the wood for the trees
    <https://www.collinsdictionary.com/dictionary/english/cant-see-the-wood-for-the-trees>`_.

    Of course, running commands in the background is the very
    *essence* of most initialisation scripts.  Their only purpose is
    to prepare the ground for the daemon to be kicked off then exit
    themselves.

    Of course, with our `systemd
    <https://www.freedesktop.org/wiki/Software/systemd/>`_ hats on,
    there's a preference for initialisation scripts to **not** run
    daemons in the background so as :program:`systemd` can better keep
    an eye on them.

In addition the system will terminate any outstanding
:ref:`asynchronous commands`.

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

Notice that we only set the handle.  We don't deal in file
descriptors, here.  If (and only if?) we get round to trying to
actually run an external command to we actually care about file
descriptors.

If we had redirected the output of some expression into a string
handle and the expression was some :lname:`Idio` code then there's no
need for any file descriptors to get involved.  Only if the expression
reduced down to an external command will we start considering file
descriptors.  In the particular case of a string handle, we need to
indirect through a temporary file as well.

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

Again, we're only dealing with handles, here, no file descriptors.

.. include:: ../../commit.rst


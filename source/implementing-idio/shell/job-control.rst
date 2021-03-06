.. include:: ../../global.rst

.. _`job control`:

***********
Job Control
***********

As mentioned before (and probably will be again) we're largely
following the directions in the :program:`info` pages on *Job Control*
(in *libc* or read the `online Job Control`_ pages) but there's a bit
more to it.

The *Job Control* documentation works pretty well for organising
single or pipelines of *external* commands.  However, :lname:`Idio` is
a programming language and even :lname:`Bash` allows you a few twirls
and twists.  Consider:

.. code-block:: console

   $ /usr/bin/echo hello | wc
         1       1       6

No real surprises (hopefully).  Now what about:

.. code-block:: console

   $ { sleep 1; echo hello; } | wc
	 1       1       6

Hmm, that's a bit more interesting.  We have a shell *Group Command*
as the first "external" process in the pipeline and I've subtly
altered the ``echo`` statement.  What's happening there?

Well, for a start the Group Command *is* in an external process as the
pipeline forces each segment of the pipeline into a child process.
But then what happens?

Well, in the right-hand child process, as the child process is just a
:manpage:`fork(2)` of the original shell then :lname:`Bash` is ready
to process what it sees.  It sees the external command :program:`wc`
but, importantly, it only sees the single command :program:`wc` so
will :manpage:`execve(2)` it in place of itself.  It is running in the
context of the pipeline, ie. its *stdin* is connected to the output of
the previous part of the pipeline.

For the left-hand child process, again, a child :lname:`Bash`, is
ready to process what it sees which is a Group Command.  The first
command in the group is the external command :program:`sleep` which
the child :lname:`Bash` process runs in the foreground -- just like it
would have in the main shell.  That's important as running a job in
the foreground also involves *fork*'ing and *exec*'ing but now it is a
child of the child :lname:`Bash`.

:program:`sleep` will slow things down for a bit.  When it completes
:lname:`Bash` sees the next command, the *builtin* command
:program:`echo` which it runs itself -- no external command with
*fork* and *exec* required.  This is important as it clearly requires
that :lname:`Bash` be running to be able to, uh, run the builtin
command.

Of course, the left-hand child process, a :lname:`Bash`, in the
pipeline has its *stdout* connected to the input of the following part
of the pipeline and, remembering that child processes inherit their
parents file descriptors, the ``hello\n`` from :program:`echo` winds
its way through to :program:`wc`.

So, whilst providing no difference in output (though possibly a
difference in timing!) we have something altogether less obvious
happening.  Whilst the pipeline is ostensibly *fork*'ing and
*exec*'ing like the *Job Control* pages suggest, in practice there's
some extra *shell*'ing in the way.

If we're a little more inquisitive we can see the two variations:

.. code-block:: console

   $ ps -Ht $(tty) | cat -
       PID TTY          TIME CMD
     67896 pts/0    00:00:00 bash
     73717 pts/0    00:00:00   ps
     73718 pts/0    00:00:00   cat

   $ { sleep 1; ps -Ht $(tty); } | cat -
       PID TTY          TIME CMD
     67896 pts/0    00:00:00 bash
     73739 pts/0    00:00:00   bash
     73743 pts/0    00:00:00     ps
     73740 pts/0    00:00:00   cat

In the first case it is just two external commands *fork*'ed and
*exec*'ed.  In the second, there is an extra :program:`bash` process
parenting the :program:`ps` which would have also parented the
:program:`sleep` but it has been and gone.

Considerations
==============

Broadly, you expect, it's a case of being a bit more careful with the
book keeping.  In our case there's also a problem with who is doing
what (and when).

.. aside::

   Unbridled enthusiasm, I'm afraid.

We'll see in :ref:`pipelines and IO` that pipelines are implemented by
a reader operator.  In other words, it's all handled in
:lname:`Idio`-land.

Almost.  In practice, the ``|`` reader operator conspires to arrange
the pipeline through a hefty but straight-forward template in which it
embeds the original code, the individual command snippets in the
pipeline.

Non-pipeline, ie. "simple" commands are handled in two ways.  If
there's a specific kind of command, eg. :ref:`collect-output` then,
again, the code is arranged in :lname:`Idio`-land with the snippet
embedded.

Any other external command *and*, therefore, those embedded snippets
are identified by the VM trying to invoke a symbol, eg. the ``ls`` in
``ls -l`` (assuming ``ls`` isn't bound to some value).  It then asks
the system to find an external command on :envvar:`PATH` by the name
of ``ls`` and then will call on the original :lname:`C` implementation
of *Job Control* to actually run the command.

So, ``echo "hello"`` will be run from the :lname:`C` implementation
and ``echo "hello" | wc`` will run through the ``|`` reader operator
creating two child :lname:`Idio` processes each of which has a splodge
of code in which are ``echo "hello"`` and ``wc`` respectively, each of
which will be run by the :lname:`C` implementation.

That's mostly saying it all boils down to the :lname:`C`
implementation to decide whether to *fork* and *exec* or just *exec*.

.. aside::

   I need a credible "yes" case!

Does it make a difference?  Hmm, mostly no except sometimes maybe yes.

How can we decide?  Well, we could decide by looking at the number of
things we're about to run.  If there's more than one then we're
probably looking to run a block of code like the Group Command
example.  One problem here is that only the :lname:`Idio`-land code
knows whether it is embedding more than one command so it would need
to flag the decision.

Even if we're only embedding a single command from :lname:`Idio`, *it*
doesn't know whether that is an external command (so can be directly
*exec*'ed) or not.  If I've imported ``libc`` then I'll get the
``libc/sleep`` primitive when I call ``sleep 1``.  We can't *exec*
primitives.

But back to that Group Command case.  Remember that the (external)
commands in the Group Command became children of the
sub-:lname:`Bash`.  So that's important (obvious but important) that
we are making our decisions about *fork*'ing and/or *exec*'ing with
respect to the "current" shell which might itself be a child of
another shell.

What *that's* trying to say is that any measure or comparison with
PIDs or PGIDs must maintain some concept of what is current.  It's not
(always) going to be the values for the original shell.

.. include:: ../../commit.rst


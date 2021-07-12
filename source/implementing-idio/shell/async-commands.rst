.. include:: ../../global.rst

.. _`asynchronous commands`:

*********************
Asynchronous Commands
*********************

.. aside::

   Although I didn't look any more closely than seeing the name and
   thinking, "I'm having that!"

The name is taken from :lname:`Bash` and reflects a different kind of
job to the usual pipeline.  Normally we expect jobs to be vaguely
task-oriented and our script is about orchestrating those tasks.

An asynchronous command, however, is sort of hiding away in the
background, a stub process waiting for us to read from or write to it.
It's a sort of adjunct service job.

For good or for ill, :lname:`Bash` is a bit easy on asynchronous
commands and whether they succeed to fail.  I've been bitten by this
where a *Process Substitution*, ``<( ... )``, was failing and it took
me a while to figure that out.

Perhaps you don't care.  I'm thinking that you should.  I went over
some of the issues in :ref:`set -e`.

Job Control
===========

.. aside::

   I *like* this thinking!

In the first instance we can extend the *job* structure to include an
*asynchronous command* flag when we know it is an asynchronous
command.

Otherwise, the job will inherit any extant job control error handling
as per the parent :lname:`Idio`.  No sense in doing anything
different.

However, we do want to behave differently if an asynchronous command
fails.  Here, because we set the asynchronous command flag, we can
trivially raise a different condition is the job failed.  In
particular, raise a ``^rt-async-command-status-error`` rather than the
normal ``^rt-command-status-error``.

To, hopefully, no-one's huge surprise, the new async condition is
derived from the normal condition though that may catch you out if you
write your own ``^rt-command-status-error`` as it will pick up
``^rt-async-command-status-error`` as well.

We can now have a distinct default condition handler for the async
condition where we can choose an appropriate behaviour.

:socrates:`And that behaviour is?` Hmm.  Tricky.  The implicit
suppression of any errors by :lname:`Bash` has filled me with no
confidence about the various asynchronous processes I run.

I suppose, in the first instance I would like to be told that
something went wrong.  So, the default action for
``^rt-async-command-status-error`` is to report the job status
and... that's it.

Just report the job status.  Let's get a feel for what we're up
against before getting all picky about stuff.

There's two more options in play, here:

#. you can set the dynamic variable ``suppress-async-command-report!``
   to not-``#f`` which suppresses the warning

#. you can supercede the default handler with one of your own which
   can do whatever


Exiting
-------

As noted in :ref:`job control considerations <job control
considerations>` when :lname:`Idio` comes to exit asynchronous
commands will be handled in the same way as stopped jobs, that is
they'll be sent a SIGTERM.

Examples
========

Let's contrive some examples.  We'll use :file:`utils/bin/auto-exit`
to control the behaviour of the asynchronous command.

SIGTERM
-------

:program:`auto-exit` can be told to read two lines of input

.. code-block:: idio
   :caption: :file:`x.idio`

   oph := pipe-into auto-exit -r 2
   hprintf oph "hello\n"
   close-handle oph

Hmm, we only wrote one line and then closed our pipe to the
asynchronous process.  It's still there, though because if the script
continued:

.. code-block:: idio

   ps -Ht (collect-output tty)
       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570027  568144  570027   idio x
    570031  570027  570031     idio x
    570032  570031  570031       bash .../auto-exit -r 2
    570033  570027  570027     /usr/bin/ps -Ht /dev/pts/6

In fact, it won't go anywhere until we exit, whereon:

.. code-block:: console

   [1]$ ps -Ht $(tty)
       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570041  568144  570041   ps -Ht /dev/pts/6

Gone!

As *Job Control* is shutting down it'll walk round the list of
outstanding jobs and if any are marked as stopped or asynchronous then
it sends them a SIGTERM.

Early Bath
----------

We can have :program:`auto-exit` time-out waiting for input -- seeing
as we're not giving it any -- and exit in disgust at our poor manners.
We'll throw in a :program:`sleep` to pad things out:

.. code-block:: idio
   :caption: :file:`x.idio`

   oph := pipe-into auto-exit -r 2 -t 1
   hprintf oph "hello\n"
   close-handle oph
   ps -Ht (collect-output tty)
   sleep 2
   ps -Ht (collect-output tty)

Giving the following output:

.. code-block:: console

       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570056  568144  570056   idio x
    570059  570056  570059     idio x
    570060  570059  570059       bash .../auto-exit -r 2 -t 1
    570061  570056  570056     /usr/bin/ps -Ht /dev/pts/6
   default-racse-handler: this async job result has been ignored:
   job 570059: (auto-exit -r 2 -t 1): a?=#t
	      PID fl  status       cmd
     proc: 570059  C  (exit 142)   (auto-exit -r 2 -t 1)
     flags: C - completed; !C - not completed; S - stopped
   Real 2.024
   User 0.007
   Syst 0.031

       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570056  568144  570056   idio x
    570065  570056  570056     /usr/bin/ps -Ht /dev/pts/6

.. aside::

   Well, that's new!

So, two things, firstly the asynchronous command exited and we were
told about it.


Secondly, the command, :program:`bash`, called ``exit
142`` which *we* can interpret as signal 14 which is ``SIGALRM`` on
this system.  I would read that as :program:`bash` caught SIGALRM and
then called ``exit (128 + SIGALRM)`` rather than call ``kill (getpid
(), SIGALRM)``.

Thirdly *[sic]*, we didn't exit because the asynchronous command
failed.

We can write an ``^rt-async-command-status-error`` handler that does
exit if we want.  Perhaps, in due course, we can have an
``enable-async-command-exit-on-error!`` variable.

Quietly Does It
^^^^^^^^^^^^^^^

As noted, we can suppress the warning to get tradition shell behaviour
by setting the dynamic variable ``suppress-async-command-report!`` to
non-``#f``:

.. code-block:: idio
   :caption: :file:`x.idio`

   suppress-async-command-report! = #t
   oph := pipe-into auto-exit -r 2 -t 1
   hprintf oph "hello\n"
   close-handle oph
   ps -Ht (collect-output tty)
   sleep 2
   ps -Ht (collect-output tty)

Giving the following output:

.. code-block:: console

       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570056  568144  570056   idio x
    570066  570056  570066     idio x
    570067  570066  570066       bash .../auto-exit -r 2 -t 1
    570068  570056  570056     /usr/bin/ps -Ht /dev/pts/6
       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570056  568144  570056   idio x
    570072  570056  570056     /usr/bin/ps -Ht /dev/pts/6

As it is a dynamic variable you can create a new value transiently in
a block:

.. code-block:: idio

   {
     suppress-async-command-report! :~ #t
     ...
   }

Normal Behaviour
----------------

.. aside::

   YMMV

Of course, if the asynchronous command exits cleanly, we shouldn't see
a thing:

.. code-block:: idio
   :caption: :file:`x.idio`

   oph := pipe-into auto-exit -r 1 -t 1
   hprintf oph "hello\n"
   close-handle oph
   ps -Ht (collect-output tty)
   sleep 1
   ps -Ht (collect-output tty)

Giving the following output:

.. code-block:: console

       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570096  568144  570096   idio x
    570113  570096  570113     [idio]
    570114  570096  570096     /usr/bin/ps -Ht /dev/pts/6
       PID    PPID    PGID COMMAND
    568144  568143  568144 bash
    570096  568144  570096   idio x
    570120  570096  570096     /usr/bin/ps -Ht /dev/pts/6

It's possible you might see the about-to-exit :program:`auto-exit` in
the first :program:`ps` output as timing is everything.  It
*shouldn't* appear in the second!

I guess it's even possible that things could be grinding so slowly on
your machine that we fail to run ``hprintf`` before the 1 second
timeout on :program:`bash`'s ``read`` builtin expires.  *Meh!* At
least you'll now get a warning!


.. include:: ../../commit.rst


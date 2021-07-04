.. include:: ../global.rst

####################
Implementation Notes
####################

On the actual implementation front, several of the subsystems may
require simultaneous production.  Obviously, that isn't possible so
some form of acceptable substitute will be required for anyone
following on themselves.  For example, instead of an error handling
subsystem that (often!) brings the system back to a sane state it
might be required to print a message to *stderr*, dump the machine
state and exit (non-zero, of course).

In one sense, this treatise is going to work in reverse as several key
decisions are dependent of the final implementation's form.  So we'll
start by describing the virtual machine then the reader and evaluator
which transform the :lname:`Idio` language into something processable
by the VM, then a section on garbage collection before the only useful
part of the whole thing, the different types of values in the system.

Help, in the form of everyone's favourite debugging tool,
:manpage:`printf(3)`, is at hand.  Once we have the ability to
construct a string representation of an :lname:`Idio` value it became
straightforward to create a :lname:`C` function to print one out to
*stderr* using a simple format string:

.. c:function:: void idio_debug (const char *fmt, IDIO o)

which is actually a wrapper to the more generic:

.. c:function:: void idio_debug_FILE (FILE *file, const char *fmt, IDIO o)

Here :samp:`{fmt}` can only contain a single ``%s`` specification as
we have a single ``IDIO`` value.  Often I'll be using something like:

.. code-block:: c

   idio_debug ("a=%s ", a);
   idio_debug ("b=%s\n", b);

To figure out what I'm doing wrong.  Yes, it is crying out for a
varargs implementation.

``idio_debug()`` is so useful I created an :lname:`Idio` variant:
:samp:`idio-debug {fmt} {value}` -- although it has been superceded by
:ref:`printf <printf>` and friends.

There are some slight limits as the depth to which the code will
recurse through objects is restricted to minimise issues with circular
loops.

.. _idio-dump:

.. c:function:: void idio_dump (IDIO o, int detail)

(and :samp:`idio-dump {value}`) are similar except ``idio_dump()``
will print out some more developer-friendly details about the internal
structure of the :samp:`{value}` -- and then call ``idio_debug()``.


.. include:: ../commit.rst


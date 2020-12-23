.. include:: ../global.rst

##########################
Implementing :lname:`Idio`
##########################

Implementing something as complex as :lname:`Idio` involves a lot of
subsystems and the description of any one may necessarily involve the
understanding of another.  There's no easy way to describe the
"finished product" (I use both words loosely) without accepting that,
as a reader, you will have to `take some things as read
<https://en.wiktionary.org/wiki/take_something_as_read>`_ and perhaps
come back again to some sections.

Books such as :ref-title:`LiSP` (:cite:`LiSP`) describe multiple
complete implementations gradually upping the complexity with each one
in turn.  The repetitive nature is the classic methodology to pick up
the various techniques.

This treatise isn't pedagogical in that sense but simply dives
straight in.

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
:samp:`idio-debug {fmt} {value}`.

There are some slight limits as the depth to which the code will
recurse through objects is restricted to minimise issues with circular
loops.

.. _idio-dump:

.. c:function:: void idio_dump (IDIO o, int detail)

(and :samp:`idio-dump {value}`) are similar except ``idio_dump()``
will print out some more developer-friendly details about the internal
structure of the :samp:`{value}` -- and then call ``idio_debug()``.

.. toctree::
   :maxdepth: 2

   style
   virtual-machine/index
   reader/index
   evaluator/index
   garbage-collection
   idio-allocator
   idio-GC
   simple-types/index
   compound-types/index
   advanced/index
.. job-control

.. include:: ../commit.rst


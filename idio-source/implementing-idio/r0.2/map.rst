.. include:: ../../global.rst

*****************
Efficient Mapping
*****************

Not So Fast
===========


One thing to note about the IOS implementation is that it was slow.  I
mean *really* slow.  Running the test suite of over 7500 tests
including all the hairy command and job-control tests used to take,
say, 50 seconds on some chosen operating system.  The 300 or so IOS
tests added another 30 seconds!

*Ouch!*

Running with profiling enabled -- a combination of a ``make debug``
and ``--vm-reports``:

.. code-block:: sh

   make clean
   make debug && .local/bin/idio --vm-reports test
   less vm-perf.log

.. sidebox::

   In fact it revealed a lot was going wrong with recording which
   we'll come back to in the next section(s).

The output isn't especially user-friendly but you could read between
the lines that something was going wrong with the closure ``map-ph``
amongst others.

ph-of / pt-of
-------------

``map`` (or whichever of the ``#n`` closures documented in
:file:`vm-perf.log` is ``map``) is relatively rich and isn't necessary
when you just want the ``ph`` or ``pt`` of the elements in a list.
There are specific functions to do just that.

So, out of interest, I changed the IOS code to call ``ph-of ...``
instead of ``map ph ...`` (ditto ``pt-of``) -- and you can throw in a
call to ``any-null?`` too.

What a difference that made.  30 seconds down to 10 seconds.  *Whoa!*

These functions are not complex so are amenable to being re-written as
primitives.

Knock that 10 seconds down to 3 seconds.

Of course, all this is being run under the relatively costly burden of
the VM timing everything and so back in a regular non-debug build the
object tests are down to 1.something seconds.

Not great but when you consider that every ``define-class``,
``define-method`` and ``make-instance`` is off on a whirlwind of
nested CPL or specializer matching then, on reflection, it seems OK.

evaluate.idio
-------------

:file:`evaluate.idio` used to be pretty hopeless as template expansion
disappeared up its own wazoo.  However, these ``map`` changes have
made it more plausible.  Again, it's not *great* but closer to being
usable.

The :lname:`Idio` code in :file:`evaluate.idio` will supersede the
:lname:`C` code in :file:`evaluate.c` if the code is imported (or
loaded) in:

.. code-block:: sh

   .local/bin/idio --load evaluate test

Here, on my dev box, 47 seconds stretches out to 180s for the full
test suite, a nearly four-fold increase.  Looking more closely, it is
29 seconds out to 77 seconds prior to the command and job-control
tests, a little over two and a half times slower.  Evidently, the
command and job-control tests cause a deal of huffing and puffing.

.. include:: ../../commit.rst


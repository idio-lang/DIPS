.. include:: ../../global.rst

.. _`compound types`:

**************
Compound Types
**************

The compound types, ie. types that reference other types, are mostly
fairly straightforward.

In addition, the reader will construct a value from one of these
simple types.


.. toctree::
   :maxdepth: 2

   pairs-and-lists
   arrays
   hash-tables
   structures

Operators
=========

There's no easy place to put ``value-index`` -- other than close to
its most common usage which is to pick apart compound types.  The
problem is that it is:

* a reader :ref:`standard operator <standard operators>`

* relies on the advanced work of :ref:`setters` for its implementation

* sneaks in some cheeky function application methods too

.. _`value-index`:

.. idio:function:: o . i

.. idio:function:: value-index o i

   Here, in general, we want to get or set the :samp:`{i}`\ :sup:`th`
   element of :samp:`{o}`.  This means we can write more readable
   code:

   .. code-block:: idio

      arr := #[ "one" "two" "three" ]
      i := 0

      ; formal
      array-ref arr i

      ; easier to read
      arr.i

   In most cases we can assign to the indexed element.

   The possible types for ``o`` and effective accessors are:

   .. csv-table::
      :header: type, ref, set, index from
      :widths: auto

      pair, ``nth``, , 1
      string, ``string-ref``, ``string-set!``, 0
      array, ``array-ref``, ``array-set!``, 0
      hash, ``hash-ref``, ``hash-set!``, 0
      struct instance, ``struct-instance-ref``, ``struct-instance-set!``
      C/pointer, :sup:`[note 1]`, :sup:`[note 2]`

   **note 1** This requires :ref:`C Structure Identification <CSI>`
   support.

   **note 2** This requires a :ref:`setter <setters>` to be defined in
    addition to C Structure Identification.

   .. rst-class:: center

   \*

   There is a cost to this as ``value-index`` doesn't know the *type*
   of ``o`` so it has to do a some testing meaning it is a little
   slower than calling the type-specific accessor directly.

   There is another use case where :samp:`{i}` is identified as a
   function (taking one argument) where the code rewritten as
   :samp:`{i} {o}`, ie. :samp:`{i}` is applied to :samp:`{o}`.

   This form is very useful for functions such as :ref:`fields
   <fields>` which split a string using the delimiters in :var:`IFS`.

   .. warning::

      ``value-index`` is a poor choice for library writers.  In
      general, you cannot presume that a user has not defined a local
      variable that shadows your structure member name.  As an obvious
      example, accessing a structure member called ``i`` as
      :samp:`{si}.i` is quite likely to expand to :samp:`{si}.{n}` for
      some :samp:`{n}` which is the current value of the user's loop
      variable ``i``.

      ``define-struct`` will have created accessor functions such as
      ``st-i`` giving :samp:`st-i {si}`.

      For ``libc`` structures always use a quoted symbol for the
      member name, :samp:`libc/struct-tms-ref {tms} 'tms_utime`.

      Obviously, accessing specific values is fine, :samp:`{arr}.4`,
      although it will be quicker to access the underlying method
      directly, here, presumably, :samp:`array-ref {arr} 4`.

.. include:: ../../commit.rst


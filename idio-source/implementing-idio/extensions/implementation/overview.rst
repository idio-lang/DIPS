.. include:: ../../../global.rst

.. _`extensions overview`:

###################
Extensions Overview
###################

We'll use the :ref:`JSON5 extension` extension as an example which
defines a :lname:`json5` module.

.. aside::

   Inspired in the sense of re-imaging the `Unicode character lookup
   table <https://github.com/detomon/unicode-table>`_ work as
   :ref:`USI` but having gotten fed up of trying to follow the lexer,
   tokenizer, parser, values contortion I started out with naïve goals
   before quickly degenerating to my own lexer, tokenizer, parser and
   values contortion.

Inspired by Simon Schoenenberger's `standalone C library for JSON5
<https://github.com/detomon/json5>`_ I wrote a standalone JSON5
parser/generator which is then bundled into an :lname:`Idio`
extension.  The standalone part is important, for our purposes, as it
demonstrates the ability to hook-in non-:lname:`Idio` code.

There is a little hoop-jumping, perhaps, in that to provide a common
base, the standalone code needs to copy the (generated) :lname:`Idio`
:file:`src/usi.[ch]` files and uses its own, reduced,
:file:`usi-wrap.[ch]` files to create a nominal
:file:`libjson5-bare.so` shared library.

To create an :lname:`Idio` extension I've created two :lname:`C`
source files (one would have been enough!):

* :file:`json5-module.c`

  Here, I've put the error handling functions and generic module
  functions, ``idio_init_json5 ()`` etc..

* :file:`json5-api.c`

  Which, like :file:`src/lib-api.c`, provides :lname:`Idio` primitives
  for the underlying JSON5 library functions.

The core JSON5 library files, :file:`json5-token.[ch]` etc. are
identical for the standalone and :lname:`Idio` libraries and make no
reference to :lname:`Idio` features.

Ideally, both the :lname:`Idio` module and the standalone code would
call the same :file:`libjson5.so` but in this case we have re-used the
USI code which would make things a mess.

How and When?
=============

How and when do we know if there is a dynamic shared library to be
loaded?  There's lots of possible mechanisms so let's consider
something really basic.

In the bowels of the loader there's a table of *readers* and
*evaluators* by filename *extension*.  In practice there's only one
reader and evaluator, today, but we can imagine, say, a reader for
pre-compiled :lname:`Idio` code.

We can extend that table, initially for an extension of :file:`.so`
with some dummy reader -- there's no :lname:`Idio` "reading" (as in
REPL) to be done for a shared library -- with, and this is our choice,
the :file:`.so` extension coming first.  We can further extend the
table with prefixes and suffixes so that we can try a variety of
constructed filenames from a given root, eg. :file:`lib{foo}.so` and
:file:`{foo}.idio` from the original request to :samp:`load {foo}`.

If, then, when we say ``load json5``, we find :file:`libjson5.so` (and
the "reader" is our dummy reader) then we can choose to
:manpage:`dlopen(3)` the shared library and initialise it.

Extending this mechanism a little further and, again, our choice, we
can say, "surely the user will have an associated :lname:`Idio` file
containing relevant functionality?"  and, look for an *adjacent*
:file:`json5.idio` file to be loaded with the normal :lname:`Idio`
reader and evaluator.

Note that that is an adjacent :file:`.idio` file and not one in a far
flung :envvar:`IDIOLIB` directory.  The idea being that these two were
installed and meant to be run together.  Who knows what that other
:file:`json5.idio` file is expecting?

Obviously, the :file:`.so` and :file:`.idio` might not be in the
literally same directory but certainly in the same hierarchy in a
constructable fashion.

There are any number of problems with architecture-dependent files
(shared libraries being one such type) in shared filesystems where you
would want The Right Thing™ to happen and so we should expect
architecture-dependent and architecture-independent subtrees to form.

Modules
=======

.. aside::

   We like to keep a tidy ship.

The modules code is table-driven in the sense that as modules are
initialised in the :lname:`C` code-base, they register a "finalizer"
function, :samp:`idio_final_{module} ()`, which can unwind any data
structures and generally free up memory allocations.  Those finalizers
are called in reverse order of initialization.

For our extension we need to be able to hook into that mechanism so
the action immediately after loading a shared library is to
:manpage:`dlsym(3)` and call the :samp:`idio_init_{module} (void
*handle)` function, :samp:`idio_init_json5 ({handle})`, in this case.

The :samp:`void *handle` parameter is the :manpage:`dlopen(3)` return
value.  I did originally use a regular GC finalizer but it transpired
that the GC would choose an unfortunate time to invoke it, and the
corresponding :manpage:`dlclose(3)`.  Notably before the
:samp:`idio_final_{module} ()` function was attempted to be called.

That means the modules tables are extended by an optional :samp:`void
*handle` which can be :manpage:`dlclose(3)`'d at a safe time.

This also means that all extension shared libraries **must** have an
:samp:`idio_init_{module} (void *handle)` function.  Whether that
function chooses to register a finalizer is up to it.  It could be a
no-op but it must exist.

.. note::

   This function signature differs to the core :lname:`Idio` modules
   defined in :file:`src` which do not take the :samp:`void *handle`
   argument.  They weren't dynamically loaded so don't need a
   :samp:`{handle}` to be closed.

   I suppose you could change all of them to accept a :samp:`void
   *handle` and pass ``NULL`` when calling them but that would appear
   disingenuous to my eye.

Source Code
-----------

The initialising function, :samp:`idio_init_json5 (void *handle)`,
really is our only required hook -- and it needn't do anything.

However, we do want to do something for our JSON5 module so there are
some bits and pieces dotted about.

JSON5 API
^^^^^^^^^

The JSON5 lexing, tokenizing and parsing all takes place in the
:file:`json5-token.c` and related files.  Remember that this is also
standalone functionality.

* :file:`json5-unicode.c`

  We define a ``json5_unicode_string_t`` which is remarkably similar
  to an :lname:`Idio` :ref:`string <strings>` in that it is a 1-, 2-
  or 4-bytes array of Unicode code points.

  .. aside::

     Fancy that!

  The rest of the struct differs but the array format is identical to
  :lname:`Idio` meaning it is cheap to copy.

  There is also a plethora of ECMAScript-oriented tests -- partly a
  feature of JSON5's willingness to allow ECMAScript Identifiers as
  object member names but also to accommodate the various escape
  sequences that JSON5 strings support.

* :file:`utf8.c`

  This is Bjoern Hoehrmann's `DFA-based decoder
  <http://bjoern.hoehrmann.de/utf-8/decoder/dfa/>`_, again, the same
  as in :lname:`Idio` whose only real purpose is to transcribe the
  UTF-8 input stream, here, into a ``json5_unicode_string_t``

* :file:`json5-token.c`

  This constructs ``json5_value_t``\ s as part of the tokenizing.

* :file:`json5-parser.c`

  This validates the JSON5 token stream and returns the aggregated ``json5_value_t``.

  It also provides the main :lname:`C` interfaces to parse either a
  :lname:`C` string or read from a file descriptor.

Note that there is no JSON5 generator, *per se*, although the
standalone code does have one in the code that uses the library.  A
generator need only walk around the ``json5_value_t`` printing out
suitable forms.

JSON5 Module
^^^^^^^^^^^^

Ostensibly, then, we have two JSON5 parser interfaces: a file
descriptor, something we can extract from file (and pipe) handles, and
a :lname:`C` string.

We can quickly augment the latter by having a function to create a
``json5_unicode_string_t`` from an :lname:`Idio` string and separate
out the :samp:`parse (json5_unicode_string_t *)` from the :samp:`parse
(char *)` interfaces and, `hey presto
<https://www.collinsdictionary.com/dictionary/english/hey-presto>`_,
we have the ability to parse :lname:`Idio` strings as JSON5.

That's not quite enough on two parts:

#. the JSON5 API has left us with a ``json5_value_t`` -- albeit one
   that has fairly direct associations with :lname:`Idio` values

   It's easy enough, of course, to walk over the ``json5_value_t``
   creating the corresponding :lname:`Idio` values as we go.

#. there's no generator

This time, the generator is slightly more complex.  At no time has
:lname:`Idio` seen a "native" JSON5 value.  JSON5 is a data
interchange format and the UTF-8 byte stream has been reified into an
:lname:`Idio` value.

The ``json5_value_t`` was an intermediate form.  As it happens, that's
all the standalone code needs but it is of no use in :lname:`Idio` as
:lname:`Idio` wants :lname:`Idio` values.

Clearly, what we want is for an :lname:`Idio` value to be serialised
as a UTF8 stream.  :lname:`Idio` values can be quite rich -- a closure
can be the key or value of a hash table, say -- so the generator needs
to be slightly leery about what is valid JSON5 as it walks over the
:lname:`Idio` value.

In fact, we can be a little bit more generous and offer a JSON (rather
than JSON5) generator as well which limits the set of valid values
further.

Errors
^^^^^^

The final missing part is error handling.  In the standalone code, the
``json5_error_printf ()`` function prints the message and calls ``exit
(1)`` which suffices for its use case.

In our case we want to replace those with raising conditions but that
raises a thorny problem itself.  After lots of iterations I finally
had the :lname:`C` code invoke the :lname:`Idio` function
``condition-report`` to normalize the way conditions are, um,
reported.

That's great except this JSON5 module wants to create new conditions
so we need some way of hooking these new conditions in.

On the :lname:`C` side, the code looks no different to any other
module.  Or rather would look no different except that all of the
conditions are bundled into :file:`src/condition.[ch]`.  That's purely
an administrative choice, the definitions of the conditions could have
been scattered about the code-base like everything else.

So, all we need do is declare the condition and then call the
definition macro:

.. code-block:: c

   IDIO_DEFINE_CONDITION0 (idio_condition_rt_json5_error_type, "^rt-json5-error", idio_condition_runtime_error_type);

where it is just another descendent of ``^runtime-error``.

This is where automatically loading the adjacent :file:`json5.idio` is
useful as we can invoke the ``define-condition-type-accessors-only``
calls there.

We still don't have anything for ``condition-report``, though.  For
that we've had to augment it with a helper function,
``condition-report-extend`` which records a callback function to be
called when a particular *condition type* is being reported.

As ``condition-report`` uses a couple of private functions to
construct its message those need to be passed as arguments along with
the original condition.

In the end, nothing too traumatic.

.. include:: ../../../commit.rst


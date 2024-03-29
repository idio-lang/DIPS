.. include:: ../../global.rst

*******
Handles
*******

.. aside:: This has nothing to do with `Fork Handles
           <https://en.wikipedia.org/wiki/Four_Candles>`_.

.. sidebox:: :lname:`Scheme`\ rs will know these as *ports*.

We want to read from and write to files (and file-like objects) and we
do that through *handles*.  In particular, the reader will use a
handle to read input from.

From :lname:`Scheme` we also get *string handles* a very neat
abstraction that is right up our shell-street and also means that the
reader is equally at home with string handles.

To make all that work there is a high-level interface, the *handle*,
and two low-level implementations, *file handle* and *string handle*.

The high-level interface maintains:

* a pointer to the low-level stream data -- which is
  file-/string-specific
  
* a *lookahead char* -- think `LL(1) grammars
  <https://en.wikipedia.org/wiki/LL_grammar>`_

* a line number within the stream, starting at 1

  Essentially, as bytes are consumed from the stream, any U+000A (LINE
  FEED) character causes a line number increment.

  The line number cannot be maintained and will be set to 0 (zero) if
  you ``seek`` somewhere in the stream other than position 0 (zero)
  which resets the line number to 1.

* a position (offset) within the stream -- always maintained though
  less human-friendly

* the name the user used to access the file

  For a *string handle* the name is a construction from ``input``
  and/or ``output`` (with a ``/`` if necessary), ``string-handle #``
  and a monotonically increasing number.

* the actual pathname of the file

  For a *string handle* it is the name, as above.

* a table of methods to manipulate the stream

The methods are:

- ``free`` - used when garbage collecting the handle

- ``readyp`` - a check that a character is available to be read
  without blocking

  Note it will return ``#t`` for interactive handles at end-of-file.

- ``getc`` - analogous to :manpage:`fgetc(3)`

- ``eofp`` - analogous to :manpage:`feof(3)`

- ``close`` - analogous to :manpage:`close(2)`

- ``putc`` - analogous to :manpage:`fputc(3)`

- ``puts`` - analogous to :manpage:`fputs(3)`

- ``flush`` - analogous to :manpage:`fflush(3)`

- ``seek`` - analogous to :manpage:`fseek(3)`

  There isn't a ``tell`` low-level method as all the other methods
  studiously update the stream's position in the high-level interface
  and :samp:`handle-pos {handle}` will return it

- ``print`` - a mechanism to convert an object to a string and
  ``puts`` that to the stream

  To note, here, is that the object is considered to be *displayed* --
  in other words, *strings* are not double-quoted.

We can now define a *handle* abstraction that almost everything else
will use and two specific implementations.

That's the basic :lname:`Scheme` model but we can (and must!) extend
it for our own nefarious shell-like purposes.  Our obvious first need
is to be able to write into or read from commands and the obvious
implementation is a :manpage:`pipe(2)`.

Hence we get *pipe handles* which are a variation on a *file handle*
re-using most methods as, ultimately, they are simple wrappers around
standard operating system file descriptors.  The only useful
difference is that you cannot *seek* on a pipe handle.

As a handy generic form, there are *fd handle* primitives, ie. file
descriptor handle primitives, which are useful generic tests for
either a file or a pipe handle.

You can imagine other file descriptor types will be available in due
course.

Implementation
==============

Following the above description the two sets of interfaces and
accessors are reasonably straightforward:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_handle_methods_s {
       void (*free)      (struct idio_s *h);
       int (*readyp)     (struct idio_s *h);
       int (*getc)       (struct idio_s *h);
       int (*eofp)       (struct idio_s *h);
       int (*close)      (struct idio_s *h);
       int (*putc)       (struct idio_s *h, int c);
       ptrdiff_t (*puts) (struct idio_s *h, char *s, size_t slen);
       int (*flush)      (struct idio_s *h);
       off_t (*seek)     (struct idio_s *h, off_t offset, int whence);
       void (*print)     (struct idio_s *h, struct idio_s *o);
   } idio_handle_methods_t;

   #define IDIO_HANDLE_FLAG_NONE		0
   #define IDIO_HANDLE_FLAG_READ		(1<<0)
   #define IDIO_HANDLE_FLAG_WRITE		(1<<1)
   #define IDIO_HANDLE_FLAG_CLOSED		(1<<2)
   #define IDIO_HANDLE_FLAG_FILE		(1<<3)
   #define IDIO_HANDLE_FLAG_PIPE		(1<<4)
   #define IDIO_HANDLE_FLAG_STRING		(1<<5)

   typedef struct idio_handle_s {
       struct idio_s *grey;
       void *stream;			/* file/string specific stream data */
       idio_handle_methods_t *methods; /* file/string specific methods */
       int lc;				/* lookahead char */
       off_t line;			/* 1+ */
       off_t pos;			/* position in file: 0+ */
       struct idio_s *filename;		/* filename the user used */
       struct idio_s *pathname;		/* pathname or some other identifying data */
   } idio_handle_t;

   #define IDIO_HANDLE_GREY(H)		((H)->u.handle->grey)
   #define IDIO_HANDLE_STREAM(H)	((H)->u.handle->stream)
   #define IDIO_HANDLE_METHODS(H)	((H)->u.handle->methods)
   #define IDIO_HANDLE_LC(H)		((H)->u.handle->lc)
   #define IDIO_HANDLE_LINE(H)		((H)->u.handle->line)
   #define IDIO_HANDLE_POS(H)		((H)->u.handle->pos)
   #define IDIO_HANDLE_FILENAME(H)	((H)->u.handle->filename)
   #define IDIO_HANDLE_PATHNAME(H)	((H)->u.handle->pathname)
   #define IDIO_HANDLE_FLAGS(H)		((H)->tflags)

   #define IDIO_INPUTP_HANDLE(H)	(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_READ)
   #define IDIO_OUTPUTP_HANDLE(H)	(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_WRITE)
   #define IDIO_CLOSEDP_HANDLE(H)	(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_CLOSED)
   #define IDIO_FILEP_HANDLE(H)		(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_FILE)
   #define IDIO_PIPEP_HANDLE(H)		(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_PIPE)
   #define IDIO_STRINGP_HANDLE(H)	(IDIO_HANDLE_FLAGS(H) & IDIO_HANDLE_FLAG_STRING)

   #define IDIO_HANDLE_M_FREE(H)	(IDIO_HANDLE_METHODS (H)->free)
   #define IDIO_HANDLE_M_READYP(H)	(IDIO_HANDLE_METHODS (H)->readyp)
   #define IDIO_HANDLE_M_GETC(H)	(IDIO_HANDLE_METHODS (H)->getc)
   #define IDIO_HANDLE_M_EOFP(H)	(IDIO_HANDLE_METHODS (H)->eofp)
   #define IDIO_HANDLE_M_CLOSE(H)	(IDIO_HANDLE_METHODS (H)->close)
   #define IDIO_HANDLE_M_PUTC(H)	(IDIO_HANDLE_METHODS (H)->putc)
   #define IDIO_HANDLE_M_PUTS(H)	(IDIO_HANDLE_METHODS (H)->puts)
   #define IDIO_HANDLE_M_FLUSH(H)	(IDIO_HANDLE_METHODS (H)->flush)
   #define IDIO_HANDLE_M_SEEK(H)	(IDIO_HANDLE_METHODS (H)->seek)
   #define IDIO_HANDLE_M_PRINT(H)	(IDIO_HANDLE_METHODS (H)->print)

   
Lookahead Char
--------------

When I first implemented this in :lname:`C`-mode, I could note that:

    :manpage:`fgetc(3)` returns either an ``unsigned char`` cast to an
    ``int`` or the sentinel value ``EOF``.  We require a sentinel
    value for our lookahead char and ``EOF`` is as handy for us as it
    was for :manpage:`fgetc(3)`.  So, if the lookahead char is ``EOF``
    it actually means call :manpage:`fgetc(3)` to get the next char.

However, UTF-8 laughs at our simple plan.  Or my :lname:`C` laughs at
me.  Either way, 0xff -- which will be recast to -1, aka, ``EOF`` --
is invalid UTF-8 but it is explicitly used *because* it is invalid in
UTF-8 test cases.  So we have to be able to handle -1/``EOF`` as a
viable, if invalid, char.

The upshot of which is, we can't have a sentinel value in the
lookahead char but have to explicitly call the ``eofp`` method
instead.  Hardly the end of the world!  (But *close*, right?)

Handles
-------

Nothing creates a *handle* directly.  Instead *file-handles*, *pipe
handles* or *string-handles* are created which, in turn, create a
*handle*.

So you :samp:`open-input-file {name}` (where :samp:`{name}` is a
string) and get in return a *handle* of the *file handle* variety.
Similarly, ``open-output-string`` returns a *handle* of the *string
handle* variety.

You can now run any of the plethora of handle-oriented operations on
either.

Reading
^^^^^^^

There is no reader input form for a *handle*.

Writing
^^^^^^^

As there is no reader input form then if we print a *handle* out it'll
take a ``#<...>`` (invalid reader) form.

For a handle we can print out some useful info like:

* the type: ``H`` for handle

* open or closed: ``o``/``c``

* file, pipe or string: ``f``/``p``/``S``

  ``S`` is used for string as in readiness for a :manpage:`socket(2)`
  based handle then ``f``, ``p`` and ``s`` match up nicely with the
  ``f?``, ``p?`` and ``s?`` predicates.

* open for reading and/or writing: ``r`` and/or ``w``

* some *fd handle* flags:

  * ``O_CLOEXEC`` or not:  ``e``/``!``

    ``e`` here matching the ``e`` mode flag passed to the ``open-*``
    commands

  * ``i`` if the handle is interactive

  * ``F`` if the handle is an original *stdio* handle (``stdin``,
    ``stdout`` or ``stderr``) with the ``F`` a mnemonic for the
    :lname:`C` ``FILE*`` object

  * ``E`` if the handle is registered as EOF

  * the file descriptor

* some *handle* details

  * the name (the user used -- or we concocted)

  * the line number

  * the position

Which might give us:

.. code-block:: idio-console

   Idio> (current-input-handle)
   #<H ofr!iF   0:"*stdin*":2:23>

   Idio> osh := (open-output-string)
   #<H oSw:"output string-handle #1889":1:0>

In the first instance, ``#<H ofr!iF   0:"*stdin*":2:23>`` we can see the
value is:

* a handle

* open

* a file

* open for read

* does not have ``O_CLOEXEC`` set (by us, anyway)

* is interactive

* is constructed from the original STDIO set

* the file descriptor is 0

* the handle's name is ``*stdin*``

* we are on line 2

* position 23

In the second case, ``#<H oSw:"output string-handle #1889":1:0>`` we can infer:

* it's a handle

* open

* a string

* writeable

* it's the 1889\ :sup:`th` *string handle* this process has created

* we're on line 1

* position 0

File Handles
------------

File handles *were* implemented using :lname:`libc`'s ``FILE`` type
and you could imagine that all the implementation methods were
essentially the :lname:`libc` equivalents.

However, the introduction of pipe handles (and some recurring "issues"
with what was, in effect, double buffered input and output) has had
them rewritten as native :manpage:`read(2)`, :manpage:`write(2)` and
friends.

The file handle stream data is:

.. code-block:: c

   #define IDIO_FILE_HANDLE_FLAG_NONE		0
   #define IDIO_FILE_HANDLE_FLAG_EOF		(1<<0)
   #define IDIO_FILE_HANDLE_FLAG_INTERACTIVE	(1<<1)
   #define IDIO_FILE_HANDLE_FLAG_STDIO		(1<<2)
   #define IDIO_FILE_HANDLE_FLAG_CLOEXEC	(1<<3)

   typedef struct idio_file_handle_stream_s {
       int fd;
       IDIO_FLAGS_T flags;		/* IDIO_FILE_HANDLE_FLAG_* */
       char *buf;			/* buffer */
       int bufsiz;
       char *ptr;			/* ptr into buffer */
       int count;			/* bytes in buffer */
   } idio_file_handle_stream_t;

Of note here is that we buffer data to and from the stream --
essentially we've re-implemented STDIO!

There is a generic file opening method:

.. code-block:: c

   static IDIO idio_open_file_handle (IDIO filename,
				      char *pathname,
				      int fd,
				      int h_type,
				      int h_flags,
				      int s_flags);

with:

* ``filename`` the name the user supplied

* ``pathname`` the "real" name of the opened file -- this might be
  ``*stdin*``, for example

* ``fd`` is the file descriptor

* ``h_type`` is ``IDIO_HANDLE_FLAG_FILE``, ``IDIO_HANDLE_FLAG_PIPE``
  etc..

* ``h_flags`` are *handle* flags as per the ``struct idio_handle_s``
  structure definition

* ``s_flags`` are the (*file handle*) stream-specific flags as seen
  above, such as a flag if the file handle is interactive.

Of interest, :samp:`static IDIO idio_open_std_file_handle (FILE
*filep)` is used to alternately wrapper the usual three STDIO
variables, ``stdin``, ``stdout`` and ``stderr``, with a :lname:`Idio`
*handle*.  The handle's name is set to be ``*stdin*``, ``*stdout*`` or
``*stderr*``.

*File handles* need a *finalizer* which will :manpage:`close(2)` the
contained file descriptor when the GC is trying to free the
corresponding *handle*.

file-handle.c
^^^^^^^^^^^^^

:file:`src/file-handle.c` contains a bundle of functions relating to
the business of finding :lname:`Idio` library files.

We will have the usual sort of library search list environment
variable, cleverly called ``IDIOLIB``.  When a user *loads* a library
file we need to find it.

.. note::

   Before I read of `an issue with systemd
   <https://news.ycombinator.com/item?id=27893181>`_ I had some
   preconceived notions about ``PATH_MAX``.

   I still do, but hopefully fewer incorrect ones.  If I understand
   things correctly then ``PATH_MAX`` is a (:lname:`glibc`?)
   constraint on user-supplied pathnames (as distinct from filenames
   in directory entries) but is not a constraint on the pathnames
   retrievable from the filesystem.

   Causing a bit more fun, ``PATH_MAX`` is probably, in reality,
   filesystem-dependent, see :manpage:`pathconf(3)`, and may return a
   very large number indeed with the suggestion being there is no
   limit in the general case.

   As to how to :manpage:`open(2)` a file that has a pathname more
   than ``PATH_MAX - 1`` bytes you'll need to refactor the original
   pathname into leading directory segments, each up up to
   ``PATH_MAX - 1`` bytes, and make repeated calls to
   :manpage:`openat(2)`.

   There is a similar note in "APPLICATION USAGE" in
   :manpage:`pwd(1p)`.

Most of that work is delegated to ``idio_libfile_find_C(char *file)``
which potters about worrying about:

* splitting ``IDIOLIB`` into directory entries

* ``PATH_MAX`` when appending name elements

* various library file extensions

  The obvious extension is ``.idio`` but we might have other forms,
  for example, a compiled format which may require a different
  *reader*.  Consequently there is, elsewhere, a table of
  :samp:`({extension}, {reader}, {evaluator})` tuples.

.. rst-class:: center

---

There were two file loading mechanisms which derived from me changing
my mind.

Consider *how* we read and evaluate files (technically, *handles* but
we're all used to thinking about files).  We could:

.. code-block:: idio-console

   while read expression
       evaluate expression
       run expression

or

.. code-block:: idio-console

   read all expressions
   evaluate all expressions
   run all expressions

I liked the latter as it solved a recurring problem I have when
developing scripts, the sort of scripts that take a minute or twenty
to chunter through yet you've spotted a :strike:`bug`\ feature just
after it's started and edit the script.  Of course you save the script
with a satisfying *kerthunk!*...while the script is still running.
Oops.  The next read from the file by :lname:`Bash` will get a garbled
string.  It's all gone pear-shaped.

I ran, for a long time, with the latter, "all in one," then changed my
mind (and deleted it).  :socrates:`Why?  What's the difference?`

The problem is subtle and primarily affects *templates*, indeed,
anything that has a meta-effect on the program, like *operators*.

The problem is that we say "evaluate" but what we really mean is:

* determine the meaning of the expression

* implement any template *use*

* prep the code for the VM

But *running* the code in the VM may or may not happen *now*.

If I *define* a template then I cannot *use* it until the code for the
definition is *run* -- which will add to the list of "expander" terms
that the evaluator will recognise.  That means I cannot *use* the
template until the byte code is run by the VM.

That might not sound like a big problem but it does prevent you
defining and using a macro within a module: for the latter variant,
the definition isn't run until we've read and evaluated everything.
In other words the evaluator will not have been informed that this new
template exists until we've hit the end of the file and can run all
the statements.

Part of this might arise from me not having written enough gnarly code
to require a template to be defined and used in the same module but
when porting :lname:`Scheme` code you quickly discover that other
people are altogether more with it.

.. rst-class:: center

\*

I did keep the "expression by expression" and "all in one" variants
around for a while but eventually ditched the "all in one" when
documenting :ref:`module` and realising it was `banjaxed
<https://en.wiktionary.org/wiki/banjaxed>`_ for similar reasons.

So, the normal :lname:`C` file loading function is:

.. code-block:: c

   IDIO idio_load_file_name (IDIO filename, IDIO cs)

and its :lname:`Idio` equivalent :samp:`load {filename}` will load
"expression by expression."

Pipe Handles
------------

We would like to read from and write to external commands for which we
need to pipe their output from them or pipe our output to them.
Maintaining the *handle*-style is important, hence pipe handles.

The implementation of pipe handles will hold no surprises,
``open-input-pipe`` is essentially the ``open-input-file-from-fd``
style of construction.

.. note::

   There is obvious naming confusion with pipes in that the output
   from a command will be an input handle as we are reading from that
   input stream.  Similarly the input to a pipe will be an output
   handle.

   So ``pipe-into`` returns an output handle and ``pipe-from`` returns
   an input handle.

A more intriguing question is how do we do this for the user?

We're a shell and, despite our use of reader operators, have a leaning
towards the :samp:`{cmd} {args}` style.  Hence, if we want to filter
the output of a command then it makes sense for us to declare that
intention as a :samp:`{cmd}`, hence:

.. sidebox::

.. code-block:: idio

   pipe-from zcat file.tgz | tar tf -

or, maybe:

.. code-block:: idio

   pipe-from tar tzf file.tgz

ie. note that this works for simple commands or pipelines.

Although what we clearly want ``pipe-from`` to do is return us a pipe
handle hence what we should have written is:

.. code-block:: idio

   ih := pipe-from zcat file.tgz | tar tf -

``ih`` is now a regular (input) *handle* that we can manipulate is
regular handle-like ways, ``read-line`` springs to mind.

``close-handle`` should also spring to mind otherwise, depending on
the scope of ``ih`` you'll be accumulating both unclosed
:manpage:`pipe(2)`\ s and a number of zombie processes.

String Handles
--------------

String handles are in some sense just the buffer part of a file
handle.  For an input string handle we will have initialised the
buffer with whatever the :samp:`{string}` argument was and with an
output string handle we just keep extending the buffer.

We can zip about inside a string handle, just like a file handle --
with the same effects on line number and position.

The string handle stream data looks like:

.. code-block:: c

   typedef struct idio_string_handle_stream_s {
       char *buf;			/* buffer */
       size_t blen;
       char *ptr;			/* ptr into buffer */
       char *end;			/* end of buffer */
       char eof;			/* EOF flag */
   } idio_string_handle_stream_t;

We don't get an end-of-file *chime* as we do with file handles so we
need to fake one up by maintaining and ``end`` of buffer marker and
"raise" end of file when we get there.

.. rst-class:: center

---

It turns out that string handles are really handy for generating error
messages within the code base from, say, a bit of :lname:`C` string
and a bit of :lname:`Idio` object.  Take, for example, the calls to
:manpage:`fdopen(3)` in :file:`src/file-handle.c`, above.

If the *system call* fails we want to raise an error condition
indicating the system call and the arguments:

.. code-block:: c
   :caption: file-handle.c

   idio_error_system_errno ("fdopen",
			    IDIO_LIST2 (idio_string_C (name),
				        idio_string_C (mode)),
			    IDIO_C_FUNC_LOCATION ());

We're passing

* a :lname:`C` string with the problem's contextual message

* an :lname:`Idio` *list* of the :samp:`{name}` associated with the
  file descriptor (defaulting to :file:`/dev/fd/X`) and the
  :samp:`{mode}` (defaulting to ``r``/``w``).

* ``IDIO_C_FUNC_LOCATION ()`` is a macro which, when compiled with
  ``DEBUG``, brings together ``__FILE__``, ``__LINE__`` and GNU's
  ``__func__`` for some handy diagnosis.

``idio_error_system_errno()`` is a wrapper to ``idio_error_system()``
with ``errno`` added as an argument and we get:

.. code-block:: c
   :caption: error.c

   void idio_error_system (char *msg, IDIO args, int err, IDIO c_location)
   {
       ...

       IDIO msh = idio_open_output_string_handle_C ();
       idio_display_C (msg, msh);
       if (idio_S_nil != args) {
	   idio_display_C (": ", msh);
	   idio_display (args, msh);
       }
       idio_display_C (": ", msh);
       idio_display_C (strerror (err), msh);

       IDIO location = idio_vm_source_location ();

       IDIO dsh = idio_open_output_string_handle_C ();
   #ifdef IDIO_DEBUG
       idio_display (c_location, dsh);
   #endif

       IDIO c = idio_struct_instance (idio_condition_system_error_type,
				      IDIO_LIST4 (idio_get_output_string (msh),
						  location,
						  idio_get_output_string (dsh),
						  idio_C_int (err)));

       idio_raise_condition (idio_S_true, c);
   }

All conditions derived from ``^idio-error`` take three standard
parameters: message, location and detail.

We can use two helper functions, ``idio_display()`` for displaying
:lname:`Idio` values and ``idio_display_C()`` for displaying
:lname:`C` strings.  Of course, at the end of some tumultuous
computation and constructing a (huge?) string in :lname:`C`,
``idio_display()`` will also be calling ``idio_display_C()``.

Here we can first create a "message" string handle, ``msh``, into
which we print (display!)  the :lname:`C` string ``msg`` (``fdopen``
in this case) then, if some ``args`` were passed, add a :lname:`C`
:literal:`: \ ` string then whatever the printed representation of the
args are.

Add on another :literal:`: \ ` then the operating system's description
of the system call error for a bit of normalised guidance.  Secondly,
recover the user-land source code location (from the *EXPR* register
in the *thread*).  Finally, we can create a "detail" string handle and
add the :lname:`C` source location if we're running under debug for
extra clarification.  The fourth parameter for a ``^system-error`` is,
in effect, ``errno``.

Finally, we can construct a condition, of the "system error" type
which is expecting a further four arguments including the
re-constituted strings from the two output string handles.

handle.c
--------

:file:`src/handle.c` is the front-end for manipulating handles and its
methods are largely just calls to the underlying file handle or string
handle methods.

Many of them differ in that they do not require a handle to be passed
to them, it is an optional argument.  The premise, here, is that the
default should be the *current input handle* or *current output
handle*.  Entities maintained by the current *thread*.

``idio_getc_handle()`` (and ``idio_ungetc_handle()``) maintain the
line and position as U+000A (LINE FEED) characters pass through.

read
^^^^

While we're here we can muse on an example of naming hell.

``read`` is a heavily overloaded name.  At our lowest level, in
:lname:`libc`, the primitive ``read`` is :manpage:`read(2)`.

However, in :lname:`Idio`, the primitive ``read`` is an invocation of
the reader, an instruction to return a complete :lname:`Idio` "line"
of input (which might be multiple lines if we have some unmatched
parentheses or braces or line continuations or ...).

We can complicate the issue with ``read-expr`` which will have the
reader consume a single expression (and not consume expressions to the
end of the line).

As a user of :lname:`Idio` I'm unlikely to call either of those and am
more likely interested in reading a line of text from a file, hence,
``read-line`` and its greedier sibling, ``read-lines``.

As a user I might also want to ``read-char`` to get back the next
(UTF-8 encoded) Unicode code point.  There is no (exposed)
``read-byte`` function.

``read`` (and ``read-expr``) isn't really used other than for testing
so I suspect they could be re-worked into a more reader-oriented name
or, indeed, namespace clearing the way for "normal" usage of the names
by users.

load
^^^^

There is a handle-variant of ``load``: ``load-handle``.

More interesting is the :lname:`C`-only
``idio_load_handle_interactive()`` which is the REPL.

Previously, I've mentioned that I don't want to spend much time here
as I'd rather target scripting, however it does get used.

I've noted above that the REPL is :lname:`C`-only in the sense that
there isn't an :lname:`Idio` entry-point.  Like most things it could
probably do with being re-arranged slightly so that there is an
:lname:`Idio` :ref:`primitive <primitives>` which calls the existing
``idio_load_handle_interactive()`` but one we could replace with a
pure-:lname:`Idio` function.

In the meanwhile, the only useful difference between the REPL and
``load-handle-ebe`` is that:

* a prompt is printed to the *current error handle*

* and the value returned by the expression is printed to the *current
  output handle*

Notably, then

#. the prompt is currently fixed to being the name of the *current
   module* followed by :literal:`> \ `, so :literal:`Idio> \ ` by
   default.  That could easily be passed off to some :lname:`Idio`
   function which might use *whatever* to construct a prompt.

   :lname:`Bash`, obviously, uses ``PS1`` with its myriad of
   baskslash-escaped special characters.

#. there is no :ref-title:`readline`-style interactive editing

   (which is annoying -- although you can fall back on
   :program:`rlwrap`)

Operations
==========

File Handles
------------

See :file:`src/file-handle.c`.

Note that when manipulating a file descriptor (rather than a file
handle) you are manipulating a ``C-int``, not a fixnum (and certainly
not a bignum).  Whilst you can construct an arbitrary ``C-int`` and
therefore "file descriptor", like regular systems programming, it
behooves the user to choose values wisely.  Normally, you would
receive such a value from a call known to provide one and pass it
around opaquely.

.. idio:function:: open-file-from-fd fd [name [mode]]

   construct a file handle from `fd` using the optional `name` instead
   of the default `/dev/fd/fd` and the optional mode `mode` instead of
   ``re``

.. idio:function:: open-input-file-from-fd fd [name]

   construct a file handle from `fd` using the optional `name` instead
   of the default `/dev/fd/fd` and the optional mode `mode` instead of
   ``re``

.. idio:function:: open-output-file-from-fd fd [name]

   construct a file handle from `fd` using the optional `name` instead
   of the default `/dev/fd/fd` and the optional mode `mode` instead of
   ``we``

.. idio:function:: open-input-pipe fd [name]

   construct a pipe handle from `fd` using the optional `name` instead
   of the default `/dev/fd/fd` and the optional mode `mode` instead of
   ``re``

.. idio:function:: open-output-pipe fd [name]

   construct a pipe handle from `fd` using the optional `name` instead
   of the default `/dev/fd/fd` and the optional mode `mode` instead of
   ``we``

.. idio:function:: open-file name mode

   construct a file handle by opening the file `name` and the mode
   `mode`

   ``open-file`` has to handle the resource contention issue mentioned
   previously.

   If the :manpage:`fopen(3)` call fails with ``EMFILE`` (a process
   limit) or ``ENFILE`` (a system-wide limit) indicating the lack of
   available file descriptors then it has to forcibly invoke the
   garbage collector and try again.

   For reasons that escape me, it tries that twice....

.. idio:function:: open-input-file name

   construct a file handle by opening the file `name` with the mode
   ``re``

.. idio:function:: open-output-file name

   construct a file handle by opening the file `name` with the mode
   ``we``

.. idio:function:: file-handle? value

   is `value` a file handle

.. idio:function:: input-file-handle? value

   is `value` a file handle capable of being read from

   Obviously this is input file handles but also files opened for
   writing with the "+" mode flag: "w+", "a+".

.. idio:function:: output-file-handle? value

   is `value` a file handle capable of being written to

   Obviously this is output file handles but also files opened for
   reading with the "+" mode flag: "r+".

.. idio:function:: file-handle-fd fh

   return the file descriptor associated with file handle `fh`

.. idio:function:: fd-handle? value

   is `value` a fd handle

.. idio:function:: input-fd-handle? value

   is `value` a fd handle capable of being read from

   Obviously this is input fd handles but also fds opened for writing
   with the "+" mode flag: "w+", "a+".

.. idio:function:: output-fd-handle? value

   is `value` a fd handle capable of being written to

   Obviously this is output fd handles but also fds opened for reading
   with the "+" mode flag: "r+".

.. idio:function:: fd-handle-fd fh

   return the file descriptor associated with fd handle `fh`

.. idio:function:: pipe-handle? value

   is `value` a pipe handle

.. idio:function:: input-pipe-handle? value

   is `value` a pipe handle capable of being read from

   The "+" mode flag is ignored for a pipe.

.. idio:function:: output-pipe-handle? value

   is `value` a pipe handle capable of being written to

   The "+" mode flag is ignored for a pipe.

.. idio:function:: pipe-handle-fd ph

   return the file descriptor associated with pipe handle `ph`

.. idio:function:: close-fd-handle-on-exec fh

   call :manpage:`fcntl(3)` on the underlying :lname:`C` file
   descriptor in fd handle `fh` with ``F_SETFD`` and ``FD_CLOEXEC``
   arguments.

.. rst-class:: center

---

.. idio:function:: find-lib filename

   search :envvar:`IDIOLIB` for `filename` using a set of possible
   filename extensions

.. idio:function:: load filename

   search :envvar:`IDIOLIB` for `filename` using a set of possible
   filename extensions and then load it in "expression by expression."

.. rst-class:: center

---

.. idio:function:: file-exists? filename

   does `filename` exist

   Technically, the test is a call to :manpage:`access(2)` with the
   ``R_OK`` flag.
      
.. idio:function:: delete-file filename

   :manpage:`remove(3)` `filename`
      

String Handles
--------------

See :file:`src/string-handle.c`.

.. idio:function:: open-input-string string

   construct an input string handle from the string `string`

.. idio:function:: open-output-string

   construct an output string handle

.. idio:function:: string-handle? value

   is `value` a string handle

.. idio:function:: input-string-handle? value

   is `value` an input string handle

.. idio:function:: output-string-handle? value

   is `value` an output string handle

.. _get-output-string:

.. idio:function:: get-output-string sh

   return a string constructed from the contents of the output string
   handle `sh`


Handles
-------

See :file:`src/handle.c`.

.. idio:function:: handle? value

   is `value` a handle

.. idio:function:: input-handle? value

   is `value` an input handle

.. idio:function:: output-handle? value

   is `value` an output handle

.. idio:function:: ready? handle

   is handle `handle` ready, ie. not at end-of-file

.. idio:function:: eof? handle

   has handle `handle` seen end-of-file

.. idio:function:: peek-char handle

   return the Unicode code point of the next character in handle
   `handle` without moving the position in the handle forward

.. idio:function:: puts value [handle]

   invoke the ``puts`` method associated with handle `handle`, if
   supplied or the *current output handle* otherwise, with `value`

   ``puts`` will use the *printed* conversion of `value` rather than
   the *displayed* version

.. idio:function:: flush-handle handle

   invoke the ``flush`` method associated with handle `handle`

.. _seek-handle:

.. idio:function:: seek-handle handle pos [whence]

   invoke the ``seek`` method associated with handle `handle` with
   `pos` and `whence`, if supplied or ``'set`` otherwise

   `whence` can be one of the *symbols* ``set``, ``end`` or ``cur``.

   See :ref:`handle-pos <handle-pos>` for the equivalent of a
   ``tell-handle``.

   Invoking ``seek-handle`` on a pipe handle will generate a
   :ref:`^rt-parameter-value-error`.

.. idio:function:: rewind-handle handle

   invoke the ``seek`` method associated with handle `handle` with a
   *position* of zero and *whence* of ``set``.

.. idio:function:: close-handle handle

   invoke the ``close`` method associated with handle `handle`

.. idio:function:: close-input-handle handle

   invoke the ``close`` method associated with input handle `handle`

.. idio:function:: close-output-handle handle

   invoke the ``close`` method associated with output handle `handle`

.. idio:function:: closed-handle? handle

   return ``#t`` if the handle `handle` has been closed and ``#f``
   otherwise

.. idio:function:: eof-object? value

   return ``#t`` if the value `value` is the end-of-file value

.. idio:function:: handle-line [handle]

   return the current line number in handle `handle` if supplied
   otherwise the current input handle

   The line number can be invalidated by a :ref:`seek-handle
   <seek-handle>` other than to position zero.

.. _handle-pos:

.. idio:function:: handle-pos [handle]

   return the current position in handle `handle` if supplied
   otherwise the current input handle

.. idio:function:: handle-location handle

   return a description of the location handle `handle` consisting of
   the handle's name, line number and position

.. idio:function:: load-handle handle

   load from handle `handle` "expression by expression."

.. rst-class:: center

---

.. idio:function:: current-input-handle

   return the current input handle

.. idio:function:: current-output-handle

   return the current output handle

.. idio:function:: current-error-handle

   return the current error handle

.. idio:function:: set-input-handle! handle

   set the current input handle to handle `handle`

.. idio:function:: set-output-handle! handle

   set the current output handle to handle `handle`

.. idio:function:: set-error-handle! handle

   set the current error handle to handle `handle`

.. rst-class:: center

---

.. idio:function:: read [handle]

   invoke the reader with handle `handle` if supplied otherwise the
   current input handle

.. idio:function:: read-expr [handle]

   invoke the expression reader with handle `handle` if supplied
   otherwise the current input handle

.. idio:function:: read-line [handle]

   return the next canonical line of text (up to a newline) as a
   string from handle `handle` if supplied otherwise the current input
   handle

.. idio:function:: read-lines [handle]

   return the remaining lines of text as a string from handle `handle`
   if supplied otherwise the current input handle

.. idio:function:: read-char [handle]

   return the UTF-8 character as a Unicode code point from handle
   `handle` if supplied otherwise the current input handle

.. _write:

.. idio:function:: write value [handle]

   invoke the ``puts`` method associated with handle `handle` if
   supplied otherwise the current input handle with `value`

   ``write`` will use the *printed* conversion of `value` rather than
   the *displayed* version.  See :ref:`display <display>` below.

.. idio:function:: write-char cp [handle]

   invoke the ``putc`` method associated with handle `handle` if
   supplied otherwise the current input handle with Unicode code point
   `cp`

   .. error::
	 
      ``putc`` doesn't generate UTF-8

.. idio:function:: newline [handle]

   invoke the ``putc`` method associated with handle `handle` if
   supplied otherwise the current input handle with Unicode code point
   U+000A (LINE FEED)

.. _display:

.. idio:function:: display value [handle]

   invoke the ``puts`` method associated with handle `handle` if
   supplied otherwise the current input handle with `value`

   ``display`` will use the *displayed* conversion of `value` rather
   than the *printed* version.  See :ref:`write <write>` above.

   A function ``display*`` (and sibling functions ``edisplay`` and
   ``edisplay*``) have been written to display multiple values
   separated by a space and with a trailing newline (to the current
   error handle).  These are largely deprecated in favour of
   :ref:`printf <printf>` (and :ref:`eprintf <eprintf>`)

.. idio:function:: %printf handle format [args]

   [deprecated in favour of :ref:`printf <printf>`]

   rudimentary support for :manpage:`printf(3)` and can only handle
   :samp:`%[{flags}][{width}][.{prec}]s` for strings (with all
   :lname:`Idio` values being converted to strings).

.. rst-class:: center

---

In :file:`lib/common.idio` there are some extra utility functions.

.. _`%format`:

.. idio:function:: %format type format [args]

   This ``%format`` function (in :file:`lib/common.idio`) makes a much
   better attempt at the vagaries of :manpage:`printf(3)` by utilising
   some dynamic variables to convey the print conversion *format* and
   *precision* to other parts of the system

   You would not normally invoke ``%format`` directly but rather use
   :ref:`format <format>` or one of the *printf* variants, below.

   `type` is one of the *symbols*:

   * ``'args`` in which case a ``%`` character in the format string
     starts an escape sequence which has the general form
     :samp:`%[{flags}][{width}][.{prec}]{K}` where :samp:`K` is a
     :manpage:`printf(3)`-ish format character with arguments in the
     parameter list `args`

     So, like a normal *printf*.  The idea being that we can print,
     say, :lname:`Idio` integers as decimal (fixnums or bignums) or
     hexadecimal, octal and binary (fixnums).

     ``%s`` should work for any :lname:`Idio` type.

   * ``'keyed`` in which case a ``%`` character in the format string
     starts an escape sequence which has the general form
     :samp:`%[{flags}][{width}][.{prec}]{K}` where :samp:`K` is a
     single Unicode code point (satisfying ``Alphabetic?``) which is
     expected to be a key in the optional hash table -- unless it is
     another ``%`` character.  The value associated with the key will
     be printed according to the specification.

   * ``'timeformat`` which is essentially the same as ``'keyed``
     except we avoid a double application of any precision

     This is to support the ``time`` function's :var:`TIMEFORMAT`
     format string which is of the form: ``"Real %.3R\nUser %.3U\nSyst
     %.3S\n"`` where ``%R``, ``%U`` and ``%S`` are now the consumed
     real time, user time and system time.

     If :samp:`K` is a ``%`` character then a ``%`` is printed
     according to the specification.

     The possible flags are:

     .. csv-table:: ``%format`` supported flags
	:widths: auto
	:align: left

	``-``, U+002D (HYPHEN-MINUS), left align the output within `width` if applicable
	:literal:`\ `, U+0020 (SPACE), use ``#\{space}`` as the left padding character
	``0``, U+0030 (DIGIT ZERO), use ``#\0`` (zero) as the left padding character

     The default padding character is ``#\{space}``.

     .. rst-class:: center

     \*

     As the start of some work to make the printer more dynamic, you
     can redefine how a struct instance or a :lname:`C` pointer is
     printed.  By default, the format is `#<SI typename fields>` where
     `fields` is a space-separated list of `fieldname:value`.

     As an alternative, you can register a "printer" against a struct
     type and it will be called when an instance of that type is
     printed.  The printer should return a string.

     By way of a simple example:

     .. code-block:: idio

	define-struct point x y

	P := make-point 1 2

	printf "%s\n" P	; #<SI point x:1 y:2>

	define (point-as-string p seen) 
	  if (point? p) {
	    r := (open-output-string)
	    hprintf r "#<SI point"
	    hprintf r " x is %d" p.x
	    hprintf r " and y is %d" p.y
	    hprintf r ">"
	    get-output-string r
	   #n
	}

	%%add-as-string point point-as-string

	printf "%s\n" P	; #<SI point x is 1 and y is 2>

     The `seen` parameter to the printer function can be used for any
     purpose.  The obvious use is to record values as they are seen
     and pass `seen` onto similar printer thus preventing circular
     loops.

     In this case, suppose `x` should be another ``point`` or ``#n``
     (rather than an integer as we seem to be using it as).  Instead
     of calling `p.x` we might call `(point-as-string x
     updated-seen)`.  To avoid loops we can add some checks and
     updates:

     .. code-block:: idio

	define (point-as-string p seen) 
	  if (point? p) {
	    if (assq p seen) {
	      "@"

	      r := (open-output-string)
	      hprintf r "#<SI point"
	      hprintf r " x is %s" (point-as-string x (pair (list p) seen))
	      hprintf r " and y is %d" p.y
	      hprintf r ">"
	      get-output-string r

	  } #n
	}

     An example is in ``state-as-string`` in
     :file:`lib/SRFI-115.idio` where the struct has an ID which can
     be used to identify where the circular loop starts (or ends?)
     rather than just returning ``"@"`` as we do.

.. _format:

.. idio:function:: format format [args]

   An invocation of `%format 'args format [args]`.

.. _hprintf:

.. idio:function:: hprintf handle format [args]

   For the ``h`` in ``hprintf`` think of the leading ``f`` in
   ``fprintf`` in :lname:`C` -- this is the generic "print to
   *handle*" variant.

   In practice it calls :ref:`display <display>` with the result of
   `format format [args]`.

.. _printf:

.. idio:function:: printf format [args]

   A call to :ref:`hprintf <hprintf>` with the *current output
   handle*.

.. _eprintf:

.. idio:function:: eprintf format [args]

   A call to :ref:`hprintf <hprintf>` with the *current error handle*.

.. _sprintf:

.. idio:function:: sprintf format [args]

   A call to :ref:`hprintf <hprintf>` with an output string handle.
   The result is a call to :ref:`get-output-string
   <get-output-string>` on that output string handle.


.. include:: ../../commit.rst


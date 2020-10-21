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

  The line number cannot be maintained if you ``seek`` somewhere in
  the stream other than position 0 (zero) which resets the line number
  to 1.

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

- ``readyp`` - broadly a check we haven't hit the end of the stream

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
   #define IDIO_HANDLE_FLAG_STRING		(1<<4)

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
"valid" char.

The upshot of which is, we can't have a sentinel value in the
lookahead char but have to explicitly call the ``eofp`` method
instead.  Hardly the end of the world!  (But *close*, right?)

Handles
-------

Nothing creates a *handle* directly.  Instead *file-handles* or
*string-handles* are created which, in turn, create a *handle*.

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

* file or string: ``f``/``s``

* open for reading and/or writing: ``r`` and/or ``w``

* some *file handle* flags:

  * ``O_CLOEXEC`` or not:  ``E``/``!``

  * the file descriptor

* some *handle* details

  * the name (the user used -- or we concocted)

  * the line number

  * the position

Which might give us:

.. code-block:: console

   Idio> (current-input-handle)
   #<H ofr!   0:"*stdin*":2:23>

   Idio> osh := (open-output-string)
   #<H osw:"output string-handle #1889":1:0>

In the first instance, ``#<H ofr!  0:"*stdin*":2:23>`` we can see the
value is:

* a handle

* open

* a file

* open for read

* does not have ``O_CLOEXEC`` set (by us, anyway)

* the file descriptor is 0

* the handle's name is ``*stdin*``

* we are on line 2

* position 23

In the second case, ``#<H osw:"output string-handle #1889":1:0>`` we can infer:

* it's a handle

* open

* a string

* writeable

* it's the 1889\ :sup:`th` *string handle* this process has created

* we're on line 1

* position 0

File Handles
------------

File handles are implemented using :lname:`libc`'s ``FILE`` type. and
you can imagine that all the implementation methods essentially the
:lname:`libc` equivalents.

The file handle stream data is:

.. code-block:: c

   #define IDIO_FILE_HANDLE_FLAG_NONE		0
   #define IDIO_FILE_HANDLE_FLAG_EOF		(1<<0)
   #define IDIO_FILE_HANDLE_FLAG_INTERACTIVE	(1<<1)
   #define IDIO_FILE_HANDLE_FLAG_STDIO		(1<<2)
   #define IDIO_FILE_HANDLE_FLAG_CLOEXEC	(1<<3)

   typedef struct idio_file_handle_stream_s {
       FILE *filep;			/* or NULL! */
       int fd;
       IDIO_FLAGS_T flags;		/* IDIO_FILE_HANDLE_FLAG_* */
       char *buf;			/* buffer */
       int bufsiz;
       char *ptr;			/* ptr into buffer */
       int count;			/* bytes in buffer */
   } idio_file_handle_stream_t;

Of note here is:

* we maintain a copy of the ``fd`` associated with ``filep`` as we use
  it with :manpage:`read(2)` to get more data from the stream

* we buffer data to and from the stream -- STDIO is buffered and we
  need to maintain a corresponding buffer

  This *can* lead to some problems with flushing recalcitrant data.  A
  problem we've all seen before, I'm sure.

There is a generic file opening method:

.. code-block:: c

   static IDIO idio_open_file_handle (IDIO filename,
				      char *pathname,
				      FILE *filep,
				      int h_flags,
				      int s_flags);

with:

* ``filename`` the name the user supplied

* ``pathname`` the "real" name of the opened file -- this might be
  ``*stdin*``, for example

* ``filep`` is the ``FILE *`` pointer

* ``h_flags`` are *handle* flags as per the ``struct idio_handle_s``
  structure definition

* ``s_flags`` are the (*file handle*) stream-specific flags as seen
  above, such as a flag if the ``FILE`` is interactive.

Of interest, :samp:`static IDIO idio_open_std_file_handle (FILE
*filep)` is used to wrapper the usual three STDIO variables,
``stdin``, ``stdout`` and ``stderr``, with a :lname:`Idio` *handle*.
The handle's name is set to be ``*stdin*``, ``*stdout*`` or
``*stderr*``.

*File handles* need a *finalizer* which will :manpage:`close(2)` the
contained file descriptor when the GC is trying to free the
corresponding *handle*.

file-handle.c
^^^^^^^^^^^^^

:file:`file-handle.c` contains a bundle of functions relating to the
business of finding :lname:`Idio` library files.

We will have the usual sort of library search list environment
variable, cleverly called ``IDIOLIB``.  When a user *loads* a library
file we need to find it.

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

There are two file loading mechanisms which derive from me changing my
mind.

Consider *how* we read and evaluate files (technically, *handles* but
we're all used to thinking about files).  We could:

.. code-block:: console

   while read expression
       evaluate expression
       run expression

or

.. code-block:: console

   read all expressions
   evaluate all expressions
   run all expressions

I ran, for a long time, with the latter, then changed my mind.
:socrates:`Why?  What's the difference?`

The problem is subtle and primarily affects *templates*, indeed,
anything that has a meta-effect on the program, like *operators*.

The problem is that we say "evaluate" but what we really mean is:

* determine the meaning of the expression

* implement any template *use*

* prep the code for the VM

But *running* the code may or may not happen *now*.

If I *define* a template then I cannot *use* it until the code for the
definition is *run* -- which will add to the list of "expander" terms
that the evaluator will recognise.  That means I cannot *use* the
template until it is run.

That might not sound like a big problem but it does prevent you
defining and using a macro within a module: for the latter variant,
the definition isn't run until we've read and evaluated everything.
In other words the evaluator will not have been informed that this new
template exists until we've hit the end of the file.

Part of this might arise from me not having written enough gnarly code
to require a template to be defined and used in the same module but
when porting :lname:`Scheme` code you quickly discover that other
people are altogether more with it.

.. rst-class:: center

\*

So, the normal :lname:`C` file loading function is:

.. code-block:: c

   IDIO idio_load_file_name_ebe (IDIO filename, IDIO cs)

and its :lname:`Idio` equivalent :samp:`load-ebe {filename}` (and
``load`` is simply a reference to ``load-ebe``).  ``ebe`` stands for
"expression by expression."

The other mechanism uses ``aio`` in place of ``ebe`` with ``aio``
standing for "all in one."

A subtle difference between the two is the extra ``IDIO cs`` argument
in :lname:`C`.  This is the list of *constants* known to the evaluator
which includes the names of things.  This will be explained later when
we get to evaluation.

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
:manpage:`fdopen(3)` in :file:`file-handle.c`, above.

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
  :samp:`{mode}` (defaulting to ``re``/``we``).

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

       IDIO dsh = idio_open_output_string_handle_C ();
       idio_display_C (strerror (err), dsh);

       IDIO c = idio_struct_instance (idio_condition_system_error_type,
				      IDIO_LIST4 (idio_get_output_string (msh),
						  c_location,
						  idio_get_output_string (dsh),
						  idio_C_int (err)));
       idio_raise_condition (idio_S_true, c);
   }

Here we can first create a "message string handle" into which we print
the :lname:`C` string ``msg`` (``fdopen`` in this case) then, if some
``args`` were passed, add a :literal:`: \ ` then whatever the printed
representation of the args are.  Secondly, we can create a "detail
string handle" and add the operating system's description of the
system call error for a bit of extra guidance.

Finally, we can construct a condition, of the "system error" type
which is expecting a further four arguments including the
re-constituted strings from the two output string handles.

handle.c
--------

:file:`handle.c` is the front-end for manipulating handles and its
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
:lname:`libc` ``read`` is :manpage:`read(2)`.

However, in :lname:`Idio`, ``read`` is an invocation of the reader, an
instruction to return a complete :lname:`Idio` "line" of input (which
might be multiple lines if we have some unmatched parentheses or
braces or line continuations or ...).

We can complicate the issue with ``read-expr`` which will have the
reader consume a single expression (and not consume expressions to the
end of the line).

As a user of :lname:`Idio` I'm unlikely to call either of those and am
more likely interested in reading a line of text from a file, hence,
``read-line`` and its greedier sibling, ``read-lines``.

As a user I might also want to ``read-char`` to get back the next
(UTF-8) character.

``read`` (and ``read-expr``) isn't really used other than for testing
so I suspect they could be re-worked into a more reader-oriented name
or, indeed, namespace clearing the way for "normal" usage of the names
by users.

load
^^^^

There are handle-variants of ``load-ebe`` and ``load-aio``:
``load-handle-ebe`` and ``load-handle-aio``.

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

See :file:`file-handle.c`.

:samp:`open-file-from-fd {fd} [{name} [{mode}]]`

      construct a file handle from :samp:`{fd}` using the optional
      :samp:`{name}` instead of the default :samp:`/dev/fd/{fd}` and
      the optional mode :samp:`{mode}` instead of ``re``

:samp:`open-input-file-from-fd {fd} [{name}]`

      construct a file handle from :samp:`{fd}` using the optional
      :samp:`{name}` instead of the default :samp:`/dev/fd/{fd}` and
      the optional mode :samp:`{mode}` instead of ``re``

:samp:`open-output-file-from-fd {fd} [{name}]`

      construct a file handle from :samp:`{fd}` using the optional
      :samp:`{name}` instead of the default :samp:`/dev/fd/{fd}` and
      the optional mode :samp:`{mode}` instead of ``we``

:samp:`open-file {name} {mode}`

      construct a file handle by opening the file :samp:`{name}` and
      the mode :samp:`{mode}`

      ``open-file`` has to handle the resource contention issue
      mentioned previously.

      If the :manpage:`fopen(3)` call fails with ``EMFILE`` (a process
      limit) or ``ENFILE`` (a system-wide limit) indicating the lack
      of available file descriptors then it has to forcibly invoke the
      garbage collector and try again.

      For reasons that escape me, it tries that twice....

:samp:`open-input-file {name}`

      construct a file handle by opening the file :samp:`{name}` with
      the mode ``re``

:samp:`open-output-file {name}`

      construct a file handle by opening the file :samp:`{name}` with
      the mode ``we``

:samp:`file-handle? {value}`

      is :samp:`{value}` a file handle

:samp:`input-file-handle? {value}`

      is :samp:`{value}` an input file handle

:samp:`output-file-handle? {value}`

      is :samp:`{value}` an output file handle

:samp:`file-handle-fd {fh}`

      return the file descriptor associated with file handle
      :samp:`{fh}`

:samp:`file-handle-fflush {fh}`

      call :manpage:`fflush(3)` on the underlying :lname:`C` ``FILE*``
      object in file handle :samp:`{fh}`

:samp:`close-file-handle-on-exec {fh}`

      call :manpage:`fcntl(3)` on the underlying :lname:`C` file
      descriptor in file handle :samp:`{fh}` with ``F_SETFD`` and
      ``FD_CLOEXEC`` arguments.

.. rst-class:: center

---

:samp:`find-lib {filename}`

      search :envvar:`IDIOLIB` for :samp:`{filename}` using a set of
      possible filename extensions

:samp:`load-ebe {filename}`

      search :envvar:`IDIOLIB` for :samp:`{filename}` using a set of
      possible filename extensions and then load it in "expression by
      expression."

      :samp:`load {filename}` is the usual interface to this function.

:samp:`load-aio {filename}`

      [deprecated]

      search :envvar:`IDIOLIB` for :samp:`{filename}` using a set of
      possible filename extensions and then load it in "all in one."

.. rst-class:: center

---

:samp:`file-exists? {filename}`

      does :samp:`{filename}` exist

      Technically, the test is a call to :manpage:`access(2)` with the
      ``R_OK`` flag.
      
:samp:`delete-file {filename}`

      :manpage:`remove(3)` :samp:`{filename}`
      

String Handles
--------------

See :file:`string-handle.c`.

:samp:`open-input-string {string}`

      construct an input string handle from the string
      :samp:`{string}`

:samp:`open-output-string`

      construct an output string handle

:samp:`string-handle? {value}`

      is :samp:`{value}` a string handle

:samp:`input-string-handle? {value}`

      is :samp:`{value}` an input string handle

:samp:`output-string-handle? {value}`

      is :samp:`{value}` an output string handle

.. _get-output-string:

:samp:`get-output-string {sh}`

      return a string constructed from the contents of the output
      string handle :samp:`{sh}`


Handles
-------

See :file:`handle.c`.

:samp:`handle? {value}`

      is :samp:`{value}` a handle

:samp:`input-handle? {value}`

      is :samp:`{value}` an input handle

:samp:`output-handle? {value}`

      is :samp:`{value}` an output handle

:samp:`ready? {handle}`

      is handle :samp:`{handle}` ready, ie. not at end-of-file

:samp:`eof? {handle}`

      has handle :samp:`{handle}` seen end-of-file

:samp:`peek-char {handle}`

      return the Unicode code point of the next character in handle
      :samp:`{handle}` without moving the position in the handle
      forward

:samp:`puts {value} [{handle}]`

      invoke the ``puts`` method associated with handle
      :samp:`{handle}`, if supplied or the *current output handle*
      otherwise, with :samp:`{value}`

      ``puts`` will use the *printed* conversion of :samp:`{value}`
      rather than the *displayed* version

:samp:`flush-handle {handle}`

      invoke the ``flush`` method associated with handle :samp:`{handle}`

.. _seek-handle:

:samp:`seek-handle {handle} {pos} [{whence}]`

      invoke the ``seek`` method associated with handle
      :samp:`{handle}` with :samp:`{pos}` and :samp:`{whence}`, if
      supplied or ``'set`` otherwise

      :samp:`{whence}` can be one of the *symbols* ``set``, ``end`` or
      ``cur``.

      See :ref:`handle-pos <handle-pos>` for the equivalent of a
      ``tell-handle``.

:samp:`rewind-handle {handle}`

      invoke the ``seek`` method associated with handle
      :samp:`{handle}` with a *position* of zero and *whence* of
      ``set``.

:samp:`close-handle {handle}`

      invoke the ``close`` method associated with handle
      :samp:`{handle}`

:samp:`close-input-handle {handle}`

      invoke the ``close`` method associated with input handle
      :samp:`{handle}`

:samp:`close-output-handle {handle}`

      invoke the ``close`` method associated with output handle
      :samp:`{handle}`

:samp:`closed-handle? {handle}`

      return ``#t`` if the handle :samp:`{handle}` has been closed and
      ``#f`` otherwise

:samp:`eof-object? {value}`

      return ``#t`` if the value :samp:`{value}` is the end-of-file
      value

:samp:`handle-line [{handle}]`

      return the current line number in handle :samp:`{handle}` if
      supplied otherwise the current input handle

      The line number can be invalidated by a :ref:`seek-handle
      <seek-handle>` other than to position zero.

.. _handle-pos:

:samp:`handle-pos [{handle}]`

      return the current position in handle :samp:`{handle}` if
      supplied otherwise the current input handle

:samp:`handle-location {handle}`

      return a description of the location handle :samp:`{handle}`
      consisting of the handle's name, line number and position

:samp:`load-handle-ebe {handle}`

      load from handle :samp:`{handle}` "expression by expression."

      :samp:`load-handle {handle}` is the usual interface to this
      function.

:samp:`load-handle-aio {handle}`

      [deprecated]

      load from handle :samp:`{handle}` "all in one."


.. rst-class:: center

---

:samp:`current-input-handle`

      return the current input handle

:samp:`current-output-handle`

      return the current output handle

:samp:`current-error-handle`

      return the current error handle

:samp:`set-input-handle! {handle}`

      set the current input handle to handle :samp:`{handle}`

:samp:`set-output-handle! {handle}`

      set the current output handle to handle :samp:`{handle}`

:samp:`set-error-handle! {handle}`

      set the current error handle to handle :samp:`{handle}`

.. rst-class:: center

---

:samp:`read [{handle}]`

      invoke the reader with handle :samp:`{handle}` if supplied
      otherwise the current input handle

:samp:`read-expr [{handle}]`

      invoke the expression reader with handle :samp:`{handle}` if
      supplied otherwise the current input handle

:samp:`read-line [{handle}]`

      return the next canonical line of text (up to a newline) as a
      string from handle :samp:`{handle}` if supplied otherwise the
      current input handle

:samp:`read-lines [{handle}]`

      return the remaining lines of text as a string from handle
      :samp:`{handle}` if supplied otherwise the current input handle

:samp:`read-char [{handle}]`

      return the UTF-8 character as a Unicode code point from handle
      :samp:`{handle}` if supplied otherwise the current input handle

.. _write:

:samp:`write {value} [{handle}]`

      invoke the ``puts`` method associated with handle
      :samp:`{handle}` if supplied otherwise the current input handle
      with :samp:`{value}`

      ``write`` will use the *printed* conversion of :samp:`{value}`
      rather than the *displayed* version.  See :ref:`display
      <display>` below.

:samp:`write-char {cp} [{handle}]`

      invoke the ``putc`` method associated with handle
      :samp:`{handle}` if supplied otherwise the current input handle
      with Unicode code point :samp:`{cp}`

      .. error::
	 
	 ``putc`` doesn't generate UTF-8

:samp:`newline [{handle}]`

      invoke the ``putc`` method associated with handle
      :samp:`{handle}` if supplied otherwise the current input handle
      with Unicode code point U+000A (LINE FEED)

.. _display:

:samp:`display {value} [{handle}]`

      invoke the ``puts`` method associated with handle
      :samp:`{handle}` if supplied otherwise the current input handle
      with :samp:`{value}`

      ``display`` will use the *displayed* conversion of
      :samp:`{value}` rather than the *printed* version.  See
      :ref:`write <write>` above.

      A function ``display*`` (and sibling functions ``edisplay`` and
      ``edisplay*``) have been written to display multiple values
      separated by a space and with a trailing newline (to the current
      error handle).  These are largely deprecated in favour of
      :ref:`printf <printf>` (and :ref:`eprintf <eprintf>`)

:samp:`%printf {handle} {format} {args}`

      [deprecated in favour of :ref:`printf <printf>`]

      rudimentary support for :manpage:`printf(3)` and can only handle
      ``%[flags][width][.precision]s`` for strings (with all
      :lname:`Idio` values being converted to strings).

.. rst-class:: center

---

In :file:`common.idio` there are some extra utility functions.

:samp:`%format {type} {format} {args}`

      This ``%format`` function (in :file:`common.idio`) makes a much
      better attempt at the vagaries of :manpage:`printf(3)` by
      utilising some dynamic variables to convey the print conversion
      *format* and *precision* to other parts of the system

      You would not normally invoke ``%format`` directly but rather
      use :ref:`format <format>` or one of the *printf* variants,
      below.

      :samp:`{type}` is one of the *symbols*:

      * ``args`` in which case a ``%`` character in the format string
        starts an escape sequence which has the general form
        :samp:`%[{flags}][{prec}][.{width}]{K}` where :samp:`{K}` is
        a :manpage:`printf(3)`-ish format character with arguments in
        ``args``

	So, like a normal *printf*.  The idea being that we can print,
	say, :lname:`Idio` integers (fixnums or bignums) as decimal,
	hexadecimal, octal and binary.

      * ``keyed`` in which case a ``%`` character in the format string
        starts an escape sequence which has the general form
        :samp:`%[{flags}][{prec}][.{width}]{K}` where :samp:`{K}` is a
        single Unicode code point (satisfying ``unicode-alphabetic?``)
        which is expected to be a key in the optional hash table --
        unless it is another ``%`` character.  The value associated
        with the key will be printed according to the specification.

      * ``timeformat`` which is essentially the same as ``keyed``
        except we avoid a double application of any precision

	This is to support the ``time`` function's
	:envvar:`TIMEFORMAT` format string which is of the form:
	``"Real %.3R\nUser %.3U\nSyst %.3S\n"`` where ``%R``, ``%U``
	and ``%S`` are now the consumed real time, user time and
	system time.

      If :samp:`{K}` is a ``%`` character then a ``%`` is printed
      according to the specification.

      The possible flags are:

      .. csv-table::
	 :widths: auto

	 ``-``, U+002D (HYPHEN-MINUS), left align the output within :samp:`{width}` if applicable
	 :literal:`\ `, U+0020 (SPACE), use ``#\{space}`` as the left padding character
	 ``0``, U+0030 (DIGIT ZERO), use ``#\0`` as the left padding character

      The default padding character is ``#\{space}``.

.. _format:

:samp:`format {format} [{args}]`

      An invocation of :samp:`%format 'args {format} [{args}]`.

.. _hprintf:

:samp:`hprintf {handle} {format} [{args}]`

      For the ``h`` in ``hprintf`` think of the leading ``f`` in
      ``fprintf`` in :lname:`C` -- this is the generic "print to
      *handle*" variant.

      In practice it calls :ref:`display <display>` with the result of
      :samp:`format {format} [{args}]`.

.. _printf:

:samp:`printf {format} [{args}]`

      A call to :ref:`hprintf <hprintf>` with the *current output
      handle*.

.. _eprintf:

:samp:`eprintf {format} [{args}]`

      A call to :ref:`hprintf <hprintf>` with the *current error
      handle*.

.. _sprintf:

:samp:`sprintf {format} [{args}]`

      A call to :ref:`hprintf <hprintf>` with an output string handle.
      The result is a call to :ref:`get-output-string
      <get-output-string>` on that output string handle.



.. include:: ../../commit.rst


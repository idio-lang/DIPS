In the *Design and Implementation of a Programmable Shell* I try to
explain how I went from an angry and frustrated SysAdmin with a head
full of bright ideas and a blank sheet of paper to an angry and
frustrated author of a programming language that functions like a
shell.

On a positive note I can only blame my own limitations in time and
talent for any problems I now have.

I take a look at the shell, where it came from, some of the historic
players and note the surprisingly busy marketplace for new shells.  I
keep forgetting to add new shells to my list so apologies to you if
I've missed you off.

I then look at *Scheme* which has provided me with the inspiration for
a solution.  Inspired-by-Scheme has taken me down some paths that are
far too complex for a shell and, probably, far too complex for what
this programming language for the Shell-People require.  But, hey.

I've set down some thoughts on my language's Look and Feel.  I'm quite
sure many people won't like some of the design choices I've made.
That said, *I* don't like some of the design choices I've made and yet
here we are.

I then get into the nitty-gritty:

* everyone has a *Virtual Machine* these days so nothing new except
  I've chosen to roll with a *Christian Queinnec*-inspired VM rather
  than targeting the Java or Perl or `$LANG` VM

  This is as much a learning experience as anything else.  I'll posit
  that we *must* be able to generate code for another VM should we so
  choose.

* we need a *reader* to turn textual source code into...something

  Here, I've added a sprinkling of fairy dust and allowed user-defined
  *operators* which can re-write the source code before it gets to the
  evaluator.  The obvious operators are infix ones like arithmetic and
  useful ones for a shell like `|`.

* we then need an *evaluator* to turn that something into putative
  code for the code generator to turn into something explicit for the
  VM

  As is the way of these things, once you're up and running, there's
  nothing to stop you re-writing the evaluator in your language, the
  *meta-circular evaluator*.

* hiding in the background of that is a need for a *Garbage Collector*

  Again, we could have targeted any of the well-known FOSS offerings
  but I'd like to see the insides, please, see how it works.

* *values*, we need *lot's* of values...

* *Job Control*

  Here, I've simply copied the GNU example code.

  Then re-written it in *Idio* itself.  Which makes it fractionally
  slower than it needs to be but on the other hand it is now exposed
  in its entirety as scripted code.

* shell features like *Process Substitution* are now derivative of
  that Job Control

* doing the heavy lifting are some wrappers to the standard library,
  `libc`

  The real trick, here, is automating the boiler-plate code generation
  meaning that it becomes relatively straight-forward to integrate any
  shared library.

  (It **can't** be effortless as there's no way to infer how to handle
  your/the standard library's interfaces and error handling but you
  can get a long way there.)

* that, of course, leads to a mechanism for handling *extensions* to
  bring in shared libraries of external code dynamically

* and then there's the bonkers stuff

  Scheme, you have led me astray!


There are probably too many words and yet, strangely, not nearly
enough.


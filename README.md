TITokens
========

`titablegen.py` reads a TokenIDE token definition file (in XML format) and produces a matching grammar for one of several targets. 

In it's primary mode of operation, a lex grammar (.l file) can be produced whose main function acts a tokenizer, and can be compiled into a native binary (or for use with webapps by means of Emscripten), and used alongside standard toolchains to produce .8xp files from the resulting .bin. 

Secondary modes of operation, accessible from the Python interpreter, produce grammars suitable for use as syntax highlighting plugins in either vim or Komodo Edit. For convenience, these are also available in compiled form as releases.

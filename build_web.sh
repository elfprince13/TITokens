#!/bin/sh

titablegen.py "$1" ForWeb > "$2_web.l" && lex -o "$2_web.yy.c" "$2_web.l" && emcc "$2_web.yy.c" -s EXPORTED_FUNCTIONS='["_yylex","_yy_scan_string","_yylex_destroy","_tEOF_Val"]' -o "$2.js"


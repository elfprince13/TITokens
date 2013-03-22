#!/bin/sh

titablegen.py "$1" > "$2.l" && lex -o "$2.yy.c" "$2.l" && gcc "$2.yy.c" -o "$2"


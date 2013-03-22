#!/usr/bin/env python  
import xml.etree.ElementTree as ET  
import sys

import re
nanum = re.compile(r'[^\w@#$&|\\;]',flags=re.UNICODE)

def get_byte(attrib):
	return int(attrib['byte'][1:],16)

def concatenate_bytes(tokbytes):
	ret = 0
	mpow = len(tokbytes)-1
	for i,byte in enumerate(tokbytes):
		ret += byte * 256**(mpow-i)
	return ret

def cleanup_chars(string):
	trouble = dict(	(i,repr(c.encode('utf-8'))[1:-1])	for i,c in enumerate(string) if ord(c) >= 128 or c == "\\")
	if trouble:
		string = "".join([c if i not in trouble else trouble[i] for i,c in enumerate(string)])
	return string

def emit_token(string,tokbytes,raw_mode=False,rootattrs=None):
	if string == r'\n' and not raw_mode:
		string = r'\n|\r\n?'
		tlen=1.5
		quotes = False
	elif string == "" and not raw_mode:
		string = "<<EOF>>"
		quotes = False
		tlen = 0
	else:
		quotes = True
		tlen = len(string)
		string = cleanup_chars(string)
	string = "".join([i for i in ['"',string.replace('"',r'\"'),'"'] if quotes or i!='"'])
	return (tlen,string,tokbytes,rootattrs) if raw_mode else ((tlen,'%s\t{\treturn 0x%X;\t}' % (string, concatenate_bytes(tokbytes))))
		
def add_all_tokens(down_from,tokens,byte_prefix,raw_mode=False):
	for token in down_from.findall("{http://merthsoft.com/Tokens}Token"):
		bp=byte_prefix+[get_byte(token.attrib)]
		if 'string' in token.attrib:
			tokens.append(emit_token(token.attrib['string'],bp,raw_mode=raw_mode,rootattrs=token.attrib))
		for alt in token.findall("{http://merthsoft.com/Tokens}Alt"):
			tokens.append(emit_token(alt.attrib['string'],bp,raw_mode=raw_mode,rootattrs=token.attrib))
		tokens = add_all_tokens(token,tokens,bp,raw_mode=raw_mode)
	return tokens

def getET(filename):	
	ET.register_namespace("","http://merthsoft.com/Tokens")  
	return ET.parse(filename).getroot()

def classify(tokens):
	types = {'op':[],'num':[],'name':[],'control':[],'statement':[],'sigil':[],'groupers':['(',')','"','{','}','[',']'],'separators':[' ',',',':','\n'],'other':[]}
	namers = range(0x41,0x5F)+range(0x60,0x64)+[0x73,0xAA] #A-Theta, assorted variable types, Ans and Strings
	numbers = range(0x30,0x3C) # 0-9,.,E
	sigils = (0x5F, 0xEB) # ('|L','prgm')
	control = range(0xCE,0xDC)
	for olen,string,tokbytes,rootattrs in tokens:
		fb = tokbytes[0]
		nb = len(tokbytes)
		aps = string[1:-1]
		if not aps:
			continue
		us = aps.decode('string-escape').decode('utf-8')
		fc = us[0]
		lc = us[-1]
		if fb in sigils:
			types['sigil'].append(aps)
		elif fb in namers:
			types['name'].append(aps)
		elif fb in numbers:
			types['num'].append(aps)
		elif aps in types['groupers']+types['separators']:
			pass
		elif fb in control:
			types['control'].append(aps)
		elif fc != " " and olen > 1:
			types['statement'].append(aps)
		elif nanum.findall(fc) or fc == lc == " ":
			types['op'].append(aps)
		else:
			types['other'].append(aps)
	return types

def dumpLL(LL):
	for kind,tokens in LL.iteritems():
		print kind
		for token in tokens:
			print "\t",token.decode('string-escape').decode('utf-8')

def make_LudditeLexer(fname):
	root = getET(fname)
	tokens = add_all_tokens(root,[],[],raw_mode=True)
	tokentypes = classify(tokens)
	template = r"""# UDL for TIBasic

language TIBasic

family markup
sublanguage BasicML
initial IN_M_DEFAULT
# Null-transition to get into SSL state
state IN_M_DEFAULT:
/./ : redo, => IN_SSL_DEFAULT



family ssl
sublanguage TIBasic

start_style SSL_DEFAULT
end_style SSL_VARIABLE

#...

keywords = [%s]

keyword_style SSL_IDENTIFIER => SSL_WORD

'//' : paint(upto, SSL_COMMENT), => IN_SSL_COMMENT_LINE_1
'"' : paint(upto, SSL_DEFAULT), => IN_SSL_DSTRING

state IN_SSL_COMMENT_LINE_1:
/[\r\n]/ : paint(upto, SSL_COMMENT), => IN_SSL_DEFAULT

state IN_SSL_DSTRING:
'"' : paint(include, SSL_STRING), => IN_SSL_DEFAULT
/$/ : paint(upto, SSL_STRING), => IN_SSL_DEFAULT
'\r' : paint(upto, SSL_STRING), => IN_SSL_DEFAULT

token_check:
# All other keywords prefer an RE

SSL_DEFAULT: skip all
SSL_COMMENT: skip all

"""
	return template % (" ".join("'%s'" % (s.rstrip("(")) for s in tokentypes['control']))


if __name__ == '__main__':
	root = getET(sys.argv[1])
	print "%{"
	print "#define YY_DECL unsigned long tok_yylex(void)"
	print "#define MAX_TOKEN_BYTES sizeof(long)"
	print "#define tEOF 256"
	print "unsigned char multibyte[MAX_TOKEN_BYTES];"
	print "%}"
	print "%option noyywrap"
	print "%option yylineno"
	print "%%"
	tokens = add_all_tokens(root,[(0,'.\tfprintf(stderr,"Skipping Unknown Character\\n");'),(512,r'^\/\/[^\r\n]+(\n|\r\n?) /* Eat comment */;')],[])
	#print ("" if 'string' not in token.attrib else token.attrib['string']),hex(int(token.attrib['byte'][1:],16))
	#print "-----"
	for tlen,pattern in sorted(tokens,reverse=True):
		try:
			print pattern
		except UnicodeEncodeError:
			print "eek",repr(pattern)
		
	print "%%"
	print r"""// We'll want to disaggregate our bytes
// for additional context when parsing
// Note our EOF byte is NOT '\0'.
unsigned int illog(unsigned long l)
{
	unsigned char v = !!(l & (0xFF)) +
					(!!(l & (0xFF << 8)) << 1) +
					(!!(l & (0xFF << 16)) << 2) +
					(!!(l & (0xFF << 24)) << 3) +
					(!!(l & ((long)0xFF << 32)) << 4) +
					(!!(l & ((long)0xFF << 40)) << 5) +
					(!!(l & ((long)0xFF << 48)) << 6) +
					(!!(l & ((long)0xFF << 56)) << 7);
					
	register unsigned int r; // result of log2(v) will go here
	register unsigned int shift;
	r = (v > 0xF   ) << 2;		v >>= r; 
	shift = (v > 0x3   ) << 1;	v >>= shift;	r |= shift;
												r |= (v >> 1);
	return r;
	
}

unsigned short yylex(void){
	static int tokIndex = MAX_TOKEN_BYTES;
	unsigned int minDex;
	unsigned long nextTok;
	unsigned short ret;
	if(tokIndex == MAX_TOKEN_BYTES){
		nextTok = tok_yylex();
		if(nextTok > 0xff){
			minDex = MAX_TOKEN_BYTES - 1 - illog(nextTok);
			for(tokIndex = MAX_TOKEN_BYTES; tokIndex > minDex; multibyte[--tokIndex] = (unsigned char)(nextTok % 256), nextTok = nextTok / 256);
		} else if(!nextTok){
			ret = tEOF;
		} else {
			ret = (unsigned char)(nextTok % 256);
		}
	}
	if(tokIndex != MAX_TOKEN_BYTES){
		ret = multibyte[tokIndex++];
	}
	return ret;
}

int main(int argc,const char * args[])
{
	int retval = 0;
	FILE *fin, *fout;

	int insize;
	int outsize=0;
	
	unsigned char * input = NULL;
	unsigned char * output = NULL;
	
	unsigned short next;
	retval = -1;
	switch(argc){
		case 3:
			printf("%s : %s -> %s\n",args[0],args[1],args[2]);
		
			if(!(fin = fopen(args[1],"r"))){
				printf("Couldn't open input file\n");
				break;
			}
			fseek(fin, 0L, SEEK_END);
			insize = ftell(fin);
			fseek(fin, 0L, SEEK_SET);
			input = calloc(insize,sizeof(unsigned char));
			if(!input){
				printf("Couldn't buffer input");
				break;
			}
			output = calloc(insize,sizeof(unsigned char));
			if(!output){
				printf("Couldn't buffer output");
				break;
			}
			fread(input,sizeof(unsigned char),insize,fin);
			fclose(fin);
			
			if(!(fout = fopen(args[2],"wb"))){
				printf("Couldn't open output file\n");
				break;
			}
			
			yy_scan_string(input);
			while((next=yylex())!=tEOF){
				output[(outsize++)%insize] = (unsigned char)next; // tEOF is the only multibyte token to be returned
				if(!(outsize % insize)) fwrite(output,sizeof(unsigned char),insize,fout);
			}
			if(outsize % insize) fwrite(output,sizeof(unsigned char),outsize % insize,fout);
			printf("Tokenized to %d bytes\n",outsize);
			
			yylex_destroy();
			fclose(fout);
		
			retval = 0;
			break;
		default: 	printf("Usage:\t%s text_file_in bin_file_out\n",args[0]);
	
	}
	if(input) free(input);
	if(output) free(output);
	return retval;
}

"""
	
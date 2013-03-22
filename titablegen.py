#!/usr/bin/env python  
import xml.etree.ElementTree as ET  
import sys   

def get_byte(attrib):
	return int(attrib['byte'][1:],16)

def concatenate_bytes(*tokbytes):
	ret = 0
	mpow = len(tokbytes)-1
	for i,byte in enumerate(tokbytes):
		ret += byte * 256**(mpow-i)
	return ret

def emit_token(string,*tokbytes):
	if string == r'\n':
		string = r'\n|\r\n?'
		tlen=1.5
		quotes = False
	elif string == "":
		string = "<<EOF>>"
		quotes = False
		tlen = 0
	else:
		quotes = True
		tlen = len(string)
		trouble = dict(	(i,repr(c.encode('utf-8'))[1:-1])	for i,c in enumerate(string) if ord(c) >= 128 or c == "\\")
		if trouble:
			#print trouble
			string = "".join([c if i not in trouble else trouble[i] for i,c in enumerate(string)])
	string = "".join([i for i in ['"',string.replace('"',r'\"'),'"'] if quotes or i!='"'])
		
	return (tlen,'%s\t{\treturn 0x%X;\t}' % (string, concatenate_bytes(*tokbytes)))
		
def add_all_tokens(down_from,tokens,byte_prefix):
	for token in down_from.findall("{http://merthsoft.com/Tokens}Token"):
		bp=byte_prefix+[get_byte(token.attrib)]
		if 'string' in token.attrib:
			tokens.append(emit_token(token.attrib['string'],*bp))
		for alt in token.findall("{http://merthsoft.com/Tokens}Alt"):
			tokens.append(emit_token(alt.attrib['string'],*bp))
		tokens = add_all_tokens(token,tokens,bp)
	return tokens
	

if __name__ == '__main__':
	ET.register_namespace("","http://merthsoft.com/Tokens")  
	
	tree = ET.parse(sys.argv[1])  
	  
	root = tree.getroot()
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
	
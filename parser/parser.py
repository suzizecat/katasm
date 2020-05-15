from genericparser import Tokenizer
from genericparser import Token
from genericparser import TokenType

from genericparser.Parser import Word
from genericparser.Parser import Statement
from genericparser.Parser import Parser

import typing as T

class AsmParser :
	opcodes = {
		"cjmpl": "18",  # conditional jump litteral
		"jmpl" : "10",  # jump litteral > addr
		"cjmpc": "19 0000",
		"jmpc" : "11 0000",
		"halt" : "1F 0000",
		"cjmpr": "1A",
		"jmpr" : "12",
		"sca"  : "20",
		"wcl"  : "21",
		"wcr"  : "22",
		"ctr"  : "23",
		"wrl"  : "3",
		"eqr"  : "42",
		"neqr" : "43",
		"gtr"  : "44",
		"ngtr" : "45",
		"ger"  : "46",
		"nger" : "47",
		"sumr" : "48",
		"subr" : "49",
		"incr" : "4A",
		"decr" : "4B",
		"atr"  : "4E",
		"atc"  : "4F 0000",
		"nop"  : "00 0000"
	}

	def __init__(self):

		self.tokenizer : Tokenizer = Tokenizer(skip_space=True)
		self.parser : Parser = Parser()
		self.asmed_code: str = ""
		self.labels : T.Dict[str,int] = dict()
		self.alias : T.Dict[str,str] = dict()
		self.instr_cnt : int = 0
		self.mem_cnt : int = 0
		self.human: str = ""
		self.__last_cmd = ""


		def label_chk(txt : str) :
			if len(txt) > 1 :
				return txt[1:].isidentifier() and txt[0] == ":"
			else:
				return txt[0] == ":"

		def alias_chk(txt : str) :
			if len(txt) > 1 :
				return txt[1:].isidentifier() and txt[0] == "$"
			else:
				return txt[0] == "$"

		def identifier_chk(txt : str):
			return txt.isidentifier()

		def hexval_chk(txt : str):
			try :
				int(txt,16)
			except :
				return False
			else:
				return txt.isalnum()

		label 		= TokenType("Label",label_chk)
		identifier 	= TokenType("Identifier",identifier_chk)
		affectation = TokenType("Affect",lambda x : x == "=")
		alias 		= TokenType("Alias", alias_chk)
		literal_hex	= TokenType("Hexval",hexval_chk)

		self.tokenizer.add_type(label)
		self.tokenizer.add_type(alias)
		self.tokenizer.add_type(identifier)
		self.tokenizer.add_type(affectation)
		self.tokenizer.add_type(literal_hex)


		Wmnemonic = Word("Mnemonic",[identifier])
		Wjumpinstr= Word("Jump",    [identifier],[lambda x : x.data in ["jmpl","cjmpl"]])
		Walias    = Word("Alias",   [alias])
		Waffect_op= Word("Affect",  [affectation])
		Woperand  = Word("Operand", [literal_hex,alias])
		Wliteral = Word("Literal",  [literal_hex])
		Wlabel    = Word("Label",   [label])

		stmt_alias = Statement("Alias")
		stmt_alias.add_word(Walias)
		stmt_alias.add_word(Waffect_op)
		stmt_alias.add_word(Wliteral)

		stmt_label = Statement("Label")
		stmt_label.add_word(Wlabel)

		stmt_cmdonly = Statement("0OpFct")
		stmt_cmdonly.add_word(Wmnemonic)

		stmt_1op = Statement("Std1OpFct")
		stmt_1op.add_word(Wmnemonic)
		stmt_1op.add_word(Woperand)

		stmt_2op = Statement("Std2OpFct")
		stmt_2op.add_word(Wmnemonic)
		stmt_2op.add_word(Woperand)
		stmt_2op.add_word(Woperand)

		stmt_jmp2lbl = Statement("Jmp2Lbl")
		stmt_jmp2lbl.add_word(Wjumpinstr)
		stmt_jmp2lbl.add_word(Wlabel)

		self.parser.register(stmt_alias,self.on_alias)
		self.parser.register(stmt_label,self.on_label)
		self.parser.register(stmt_cmdonly, self.on_0opcmd)
		self.parser.register(stmt_1op, self.on_1opcmd)
		self.parser.register(stmt_2op, self.on_2opcmd)
		self.parser.register(stmt_jmp2lbl, self.on_jmp2lbl)

	@property
	def compressed_code(self):
		return "".join(self.asmed_code.strip().split())

	def get_literal(self, t : Token):
		if t.type == "Hexval" :
			return int(t.data,16)
		elif t.type == "Alias" :
			return int(self.alias[t.data],16)
		raise TypeError()

	def append(self,hex,viewed = None):
		self.asmed_code += f"{hex}\n"
		self.__last_cmd = hex if viewed is None else viewed


	def __msg(self,msg,level : T.List[str] = "Info",line : T.Optional[int]=None) -> str:
		l = line if line is not None else self.instr_cnt
		return f"KatAsm {level:4s}:{l:3d} - {msg}"

	def __human(self,msg : str,hide_mem = False):
		if hide_mem :
			self.human += f"{self.instr_cnt:3d} @ {'':-<3s}: [-- ----] {msg}\n"
		else :
			self.human += f"{self.instr_cnt:3d} @ {self.mem_cnt:03X}: [{self.__last_cmd}] {msg}\n"

	def on_alias(self,tk_list : T.List[Token]) -> bool:
		self.instr_cnt += 1
		name = tk_list[0].data
		value = tk_list[2].data
		self.alias[name] = value
		self.__human(f"Define alias {name} with value {value}", True)
		return True

	def on_label(self,tk_list : T.List[Token]) -> bool:
		lbl = tk_list[0].data
		self.instr_cnt += 1
		if lbl in self.labels :
			print(self.__msg(f"Redefining label {lbl}"))
		self.labels[lbl] = self.mem_cnt
		self.__human(f"Define label {lbl} for next program instruction",True)

		return True

	def on_0opcmd(self,tk_list : T.List[Token]) -> bool:
		self.instr_cnt += 1
		instr = tk_list[0].data
		self.append(AsmParser.opcodes[instr])
		if instr == "nop" :
			self.__human("No operation")
		elif instr == "jmpc":
			self.__human("Jump to cache value")
		elif instr == "cjmpc":
			self.__human("Jump conditionally to cache value")
		elif instr == "atc":
			self.__human("ALU to cache")
		elif instr == "halt":
			self.__human("Halt")
		else :
			return False

		self.mem_cnt += 1
		return True

	def on_1opcmd(self, tk_list: T.List[Token]) -> bool:
		self.instr_cnt += 1
		instr = tk_list[0].data
		opcode = AsmParser.opcodes[instr]

		op1 = self.get_literal(tk_list[1])
		if instr in ["jmpr","cjmpr"] :

			self.append(f"{opcode} 000{op1}")
			self.__human(f"Jump {'conditionally' if instr == 'cjmpr' else ''} to register {op1} value")
		elif instr in ["jmpl","cjmpl"] :
			self.append(f"{opcode} {op1:04X}")
			self.__human(f"Jump {'conditionally' if instr == 'cjmpl' else ''} to litteral {op1:04X} ")
		elif instr in ["sca"] :
			self.append(f"{opcode} {op1:04X}")
			self.__human(f"Set cache address to litteral {op1:04X} ")
		elif instr in ["wcl"]:
			self.append(f"{opcode} {op1:04X}")
			self.__human(f"Write litteral {op1:04X} to cache")
		elif instr in ["wcr","ctr"]:
			self.append(f"{opcode} 000{op1:01X}")
			self.__human(f"Write {'register to cache' if instr == 'wcr' else 'cache to register' } using register {op1:04X}")
		elif instr in ["atr"] :
			self.append(f"{opcode} 000{op1:01X}")
			self.__human(f"Write ALU result to register {op1:01X} ")
		elif instr in ["incr","decr"] :
			self.append(f"{opcode} 000{op1:01X}")
			self.__human(f"{'In' if  instr == 'incr' else 'De'}crement register {op1:01X} through ALU.")
		else :
			return False
		self.mem_cnt += 1
		return True

	def on_2opcmd(self, tk_list: T.List[Token]) -> bool:
		self.instr_cnt += 1
		instr = tk_list[0].data
		opcode = AsmParser.opcodes[instr]
		op1 = self.get_literal(tk_list[1])
		op2 = self.get_literal(tk_list[2])
		if instr in ["eqr","neqr","sumr","subr","gtr","ngtr","ger","nger"] :
			self.append(f"{opcode} 0{op1:01X}0{op2:01X}")
			self.__human(f"ALU operation {instr} between registers {op1:01X} and {op2:01X}")
		elif instr in ["wrl"] :
			self.append(f"{opcode}{op1:01X} {op2:04X}")
			self.__human(f"Write litteral {op2:04X} in register {op1:01X}")
		else :
			return False
		self.mem_cnt += 1
		return True

	def on_jmp2lbl(self, tk_list: T.List[Token]) -> bool:
		self.instr_cnt += 1
		instr = tk_list[0].data
		opcode = AsmParser.opcodes[instr]
		op1 = tk_list[1].data
		#matching_addr =  self.labels[op1]
		if instr in ["jmpl", "cjmpl"]:
			self.append(f"{opcode} {op1}\n",f"{opcode} XXXX")
			self.__human(f"Jump {'conditionally' if instr == 'cjmpl' else ''} to label {op1}")
		else :
			return False
		self.mem_cnt += 1
		return True

	def analyze(self,content : str):
		self.tokenizer.tokenize(content)
		self.parser.load(self.tokenizer.tokens)
		self.parser.run()

	def forward_label_replace(self):
		for label in self.labels :
			self.asmed_code = self.asmed_code.replace(label,f"{self.labels[label]:04x}")
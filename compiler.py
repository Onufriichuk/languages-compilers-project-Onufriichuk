import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenKind(Enum):
    IDENTIFIER = auto()
    INTEGER = auto()

    NUM32 = auto()
    NUM64 = auto()
    BOOL = auto()
    MUT = auto()
    IF = auto()
    ELSE = auto()
    TRUE = auto()
    FALSE = auto()

    ASSIGN = auto()
    EQUAL = auto()
    NOT_EQUAL = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    SEMICOLON = auto()

    EOF = auto()


@dataclass
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int


class CompilationError(Exception):
    def __init__(self, line: int, column: int, message: str):
        self.line = line
        self.column = column
        self.message = message
        super().__init__(message)


class Lexer:
    KEYWORDS = {
        "num32": TokenKind.NUM32,
        "num64": TokenKind.NUM64,
        "bool": TokenKind.BOOL,
        "mut": TokenKind.MUT,
        "if": TokenKind.IF,
        "else": TokenKind.ELSE,
        "true": TokenKind.TRUE,
        "false": TokenKind.FALSE,
    }

    def __init__(self, source: bytes):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

    def at_end(self) -> bool:
        return self.index >= len(self.source)

    def current(self) -> Optional[int]:
        if self.at_end():
            return None
        return self.source[self.index]

    def peek_byte(self, offset: int = 0) -> Optional[int]:
        position = self.index + offset
        if position >= len(self.source):
            return None
        return self.source[position]

    def advance(self) -> int:
        byte = self.source[self.index]
        self.index += 1

        if byte == ord("\n"):
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return byte

    def is_letter(self, byte: int) -> bool:
        return (
            ord("a") <= byte <= ord("z")
            or ord("A") <= byte <= ord("Z")
        )

    def is_digit(self, byte: int) -> bool:
        return ord("0") <= byte <= ord("9")

    def read_identifier(self) -> Token:
        start_index = self.index
        start_line = self.line
        start_column = self.column

        while not self.at_end():
            byte = self.current()

            if byte is None:
                break

            if self.is_letter(byte) or self.is_digit(byte) or byte == ord("_"):
                self.advance()
            else:
                break

        text = self.source[start_index:self.index].decode("utf-8")
        kind = self.KEYWORDS.get(text, TokenKind.IDENTIFIER)

        return Token(kind, text, start_line, start_column)

    def read_integer(self) -> Token:
        start_index = self.index
        start_line = self.line
        start_column = self.column

        while not self.at_end():
            byte = self.current()

            if byte is None or not self.is_digit(byte):
                break

            self.advance()

        if not self.at_end():
            byte = self.current()

            if byte is not None and (
                self.is_letter(byte) or byte == ord("_")
            ):
                raise CompilationError(
                    self.line,
                    self.column,
                    "invalid character in integer literal",
                )

        text = self.source[start_index:self.index].decode("utf-8")

        return Token(
            TokenKind.INTEGER,
            text,
            start_line,
            start_column,
        )

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while not self.at_end():
            byte = self.current()

            if byte is None:
                break

            if byte in (
                ord(" "),
                ord("\t"),
                ord("\r"),
                ord("\n"),
            ):
                self.advance()
                continue

            if self.is_letter(byte):
                tokens.append(self.read_identifier())
                continue

            if self.is_digit(byte):
                tokens.append(self.read_integer())
                continue

            line = self.line
            column = self.column

            if byte == ord(":"):
                if self.peek_byte(1) == ord("="):
                    self.advance()
                    self.advance()
                    tokens.append(
                        Token(
                            TokenKind.ASSIGN,
                            ":=",
                            line,
                            column,
                        )
                    )
                    continue

                raise CompilationError(
                    line,
                    column,
                    "expected '=' after ':'",
                )

            if byte == ord("="):
                if self.peek_byte(1) == ord("="):
                    self.advance()
                    self.advance()
                    tokens.append(
                        Token(
                            TokenKind.EQUAL,
                            "==",
                            line,
                            column,
                        )
                    )
                    continue

                raise CompilationError(
                    line,
                    column,
                    "expected '=' after '='",
                )

            if byte == ord("!"):
                if self.peek_byte(1) == ord("="):
                    self.advance()
                    self.advance()
                    tokens.append(
                        Token(
                            TokenKind.NOT_EQUAL,
                            "!=",
                            line,
                            column,
                        )
                    )
                    continue

                raise CompilationError(
                    line,
                    column,
                    "expected '=' after '!'",
                )

            single_tokens = {
                ord("+"): TokenKind.PLUS,
                ord("-"): TokenKind.MINUS,
                ord("*"): TokenKind.STAR,
                ord("/"): TokenKind.SLASH,
                ord("{"): TokenKind.LBRACE,
                ord("}"): TokenKind.RBRACE,
                ord("("): TokenKind.LPAREN,
                ord(")"): TokenKind.RPAREN,
                ord(";"): TokenKind.SEMICOLON,
            }

            if byte in single_tokens:
                self.advance()
                tokens.append(
                    Token(
                        single_tokens[byte],
                        chr(byte),
                        line,
                        column,
                    )
                )
                continue

            try:
                character = bytes([byte]).decode("utf-8")
            except UnicodeDecodeError:
                character = f"byte {byte}"

            raise CompilationError(
                line,
                column,
                f"unexpected character {character!r}",
            )

        tokens.append(
            Token(
                TokenKind.EOF,
                "",
                self.line,
                self.column,
            )
        )

        return tokens


@dataclass
class ASTNode:
    line: int
    column: int


@dataclass
class ProgramNode(ASTNode):
    statements: List["StmtNode"]


@dataclass
class StmtNode(ASTNode):
    pass


@dataclass
class ExprNode(ASTNode):
    pass


@dataclass
class DeclarationNode(StmtNode):
    var_type: str
    name: str
    mutable: bool
    value: ExprNode


@dataclass
class AssignmentNode(StmtNode):
    name: str
    value: ExprNode


@dataclass
class IfNode(StmtNode):
    condition: ExprNode
    then_body: List[StmtNode]
    else_body: Optional[List[StmtNode]]


@dataclass
class BinaryExprNode(ExprNode):
    operator: str
    left: ExprNode
    right: ExprNode


@dataclass
class IntegerNode(ExprNode):
    value: int


@dataclass
class BooleanNode(ExprNode):
    value: bool


@dataclass
class IdentifierNode(ExprNode):
    name: str


class Parser:
    TYPE_LIMITS = {
        "num32": 2147483647,
        "num64": 9223372036854775807,
    }

    TYPE_TOKENS = {
        TokenKind.NUM32,
        TokenKind.NUM64,
        TokenKind.BOOL,
    }

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = 0

    def peek(self, offset: int = 0) -> Token:
        position = self.index + offset

        if position >= len(self.tokens):
            return self.tokens[-1]

        return self.tokens[position]

    def eat(
        self,
        expected: Optional[TokenKind] = None,
    ) -> Token:
        token = self.peek()

        if expected is not None and token.kind != expected:
            raise CompilationError(
                token.line,
                token.column,
                f"expected {self.kind_name(expected)}, got {self.token_name(token)}",
            )

        self.index += 1
        return token

    def kind_name(self, kind: TokenKind) -> str:
        names = {
            TokenKind.IDENTIFIER: "identifier",
            TokenKind.INTEGER: "integer",
            TokenKind.NUM32: "'num32'",
            TokenKind.NUM64: "'num64'",
            TokenKind.BOOL: "'bool'",
            TokenKind.MUT: "'mut'",
            TokenKind.IF: "'if'",
            TokenKind.ELSE: "'else'",
            TokenKind.TRUE: "'true'",
            TokenKind.FALSE: "'false'",
            TokenKind.ASSIGN: "':='",
            TokenKind.EQUAL: "'=='",
            TokenKind.NOT_EQUAL: "'!='",
            TokenKind.PLUS: "'+'",
            TokenKind.MINUS: "'-'",
            TokenKind.STAR: "'*'",
            TokenKind.SLASH: "'/'",
            TokenKind.LBRACE: "'{'",
            TokenKind.RBRACE: "'}'",
            TokenKind.LPAREN: "'('",
            TokenKind.RPAREN: "')'",
            TokenKind.SEMICOLON: "';'",
            TokenKind.EOF: "end of file",
        }

        return names[kind]

    def token_name(self, token: Token) -> str:
        if token.kind == TokenKind.EOF:
            return "end of file"

        return repr(token.text)

    def parse(self) -> ProgramNode:
        statements: List[StmtNode] = []

        while self.peek().kind != TokenKind.EOF:
            statements.append(self.parse_statement())

        first = self.tokens[0]

        return ProgramNode(
            first.line,
            first.column,
            statements,
        )

    def parse_statement(self) -> StmtNode:
        token = self.peek()

        if token.kind in self.TYPE_TOKENS:
            return self.parse_declaration()

        if token.kind == TokenKind.IDENTIFIER:
            return self.parse_assignment()

        if token.kind == TokenKind.IF:
            return self.parse_if()

        if token.kind == TokenKind.ELSE:
            raise CompilationError(
                token.line,
                token.column,
                "unexpected 'else'",
            )

        raise CompilationError(
            token.line,
            token.column,
            "expected statement",
        )

    def parse_declaration(self) -> DeclarationNode:
        type_token = self.eat()

        mutable = False

        if self.peek().kind == TokenKind.MUT:
            self.eat(TokenKind.MUT)
            mutable = True

        name_token = self.eat(TokenKind.IDENTIFIER)

        self.eat(TokenKind.LBRACE)
        value = self.parse_expression()
        self.eat(TokenKind.RBRACE)
        self.eat(TokenKind.SEMICOLON)

        if (
            type_token.text in self.TYPE_LIMITS
            and isinstance(value, IntegerNode)
        ):
            maximum = self.TYPE_LIMITS[type_token.text]

            if value.value > maximum:
                raise CompilationError(
                    value.line,
                    value.column,
                    f"integer value {value.value} overflows {type_token.text}",
                )

        return DeclarationNode(
            type_token.line,
            type_token.column,
            type_token.text,
            name_token.text,
            mutable,
            value,
        )

    def parse_assignment(self) -> AssignmentNode:
        name_token = self.eat(TokenKind.IDENTIFIER)

        self.eat(TokenKind.ASSIGN)
        value = self.parse_expression()
        self.eat(TokenKind.SEMICOLON)

        return AssignmentNode(
            name_token.line,
            name_token.column,
            name_token.text,
            value,
        )

    def parse_if(self) -> IfNode:
        if_token = self.eat(TokenKind.IF)

        condition = self.parse_expression()

        self.eat(TokenKind.LBRACE)

        if self.peek().kind == TokenKind.RBRACE:
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "if block must contain at least one statement",
            )

        then_body: List[StmtNode] = []

        while self.peek().kind != TokenKind.RBRACE:
            if self.peek().kind == TokenKind.EOF:
                token = self.peek()
                raise CompilationError(
                    token.line,
                    token.column,
                    "expected '}' to close if block",
                )

            then_body.append(self.parse_statement())

        self.eat(TokenKind.RBRACE)

        else_body: Optional[List[StmtNode]] = None

        if self.peek().kind == TokenKind.ELSE:
            self.eat(TokenKind.ELSE)
            self.eat(TokenKind.LBRACE)

            if self.peek().kind == TokenKind.RBRACE:
                token = self.peek()
                raise CompilationError(
                    token.line,
                    token.column,
                    "else block must contain at least one statement",
                )

            else_body = []

            while self.peek().kind != TokenKind.RBRACE:
                if self.peek().kind == TokenKind.EOF:
                    token = self.peek()
                    raise CompilationError(
                        token.line,
                        token.column,
                        "expected '}' to close else block",
                    )

                else_body.append(self.parse_statement())

            self.eat(TokenKind.RBRACE)

        return IfNode(
            if_token.line,
            if_token.column,
            condition,
            then_body,
            else_body,
        )

    def parse_expression(self) -> ExprNode:
        return self.parse_equality()

    def parse_equality(self) -> ExprNode:
        left = self.parse_additive()

        while self.peek().kind in (
            TokenKind.EQUAL,
            TokenKind.NOT_EQUAL,
        ):
            operator = self.eat()
            right = self.parse_additive()

            left = BinaryExprNode(
                operator.line,
                operator.column,
                operator.text,
                left,
                right,
            )

        return left

    def parse_additive(self) -> ExprNode:
        left = self.parse_multiplicative()

        while self.peek().kind in (
            TokenKind.PLUS,
            TokenKind.MINUS,
        ):
            operator = self.eat()
            right = self.parse_multiplicative()

            left = BinaryExprNode(
                operator.line,
                operator.column,
                operator.text,
                left,
                right,
            )

        return left

    def parse_multiplicative(self) -> ExprNode:
        left = self.parse_primary()

        while self.peek().kind in (
            TokenKind.STAR,
            TokenKind.SLASH,
        ):
            operator = self.eat()
            right = self.parse_primary()

            left = BinaryExprNode(
                operator.line,
                operator.column,
                operator.text,
                left,
                right,
            )

        return left

    def parse_primary(self) -> ExprNode:
        token = self.peek()

        if token.kind == TokenKind.INTEGER:
            token = self.eat(TokenKind.INTEGER)

            return IntegerNode(
                token.line,
                token.column,
                int(token.text),
            )

        if token.kind == TokenKind.TRUE:
            token = self.eat(TokenKind.TRUE)

            return BooleanNode(
                token.line,
                token.column,
                True,
            )

        if token.kind == TokenKind.FALSE:
            token = self.eat(TokenKind.FALSE)

            return BooleanNode(
                token.line,
                token.column,
                False,
            )

        if token.kind == TokenKind.IDENTIFIER:
            token = self.eat(TokenKind.IDENTIFIER)

            return IdentifierNode(
                token.line,
                token.column,
                token.text,
            )

        if token.kind == TokenKind.LPAREN:
            self.eat(TokenKind.LPAREN)
            expression = self.parse_expression()
            self.eat(TokenKind.RPAREN)
            return expression

        raise CompilationError(
            token.line,
            token.column,
            "expected expression",
        )


def dump_ast(node: ASTNode, indent: int = 0) -> List[str]:
    prefix = "  " * indent

    if isinstance(node, ProgramNode):
        lines = [
            f"{prefix}Program line={node.line} column={node.column}"
        ]

        for statement in node.statements:
            lines.extend(
                dump_ast(statement, indent + 1)
            )

        return lines

    if isinstance(node, DeclarationNode):
        lines = [
            (
                f"{prefix}Declaration "
                f"line={node.line} column={node.column} "
                f"type={node.var_type} "
                f"name={node.name} "
                f"mutable={str(node.mutable).lower()}"
            )
        ]

        lines.append(f"{prefix}  Value")
        lines.extend(
            dump_ast(node.value, indent + 2)
        )

        return lines

    if isinstance(node, AssignmentNode):
        lines = [
            (
                f"{prefix}Assignment "
                f"line={node.line} column={node.column} "
                f"name={node.name}"
            )
        ]

        lines.append(f"{prefix}  Value")
        lines.extend(
            dump_ast(node.value, indent + 2)
        )

        return lines

    if isinstance(node, IfNode):
        lines = [
            f"{prefix}If line={node.line} column={node.column}"
        ]

        lines.append(f"{prefix}  Condition")
        lines.extend(
            dump_ast(node.condition, indent + 2)
        )

        lines.append(f"{prefix}  Then")

        for statement in node.then_body:
            lines.extend(
                dump_ast(statement, indent + 2)
            )

        if node.else_body is not None:
            lines.append(f"{prefix}  Else")

            for statement in node.else_body:
                lines.extend(
                    dump_ast(statement, indent + 2)
                )

        return lines

    if isinstance(node, BinaryExprNode):
        lines = [
            (
                f"{prefix}BinaryExpr "
                f"line={node.line} column={node.column} "
                f"operator={node.operator}"
            )
        ]

        lines.append(f"{prefix}  Left")
        lines.extend(
            dump_ast(node.left, indent + 2)
        )

        lines.append(f"{prefix}  Right")
        lines.extend(
            dump_ast(node.right, indent + 2)
        )

        return lines

    if isinstance(node, IntegerNode):
        return [
            (
                f"{prefix}Integer "
                f"line={node.line} column={node.column} "
                f"value={node.value}"
            )
        ]

    if isinstance(node, BooleanNode):
        return [
            (
                f"{prefix}Boolean "
                f"line={node.line} column={node.column} "
                f"value={str(node.value).lower()}"
            )
        ]

    if isinstance(node, IdentifierNode):
        return [
            (
                f"{prefix}Identifier "
                f"line={node.line} column={node.column} "
                f"name={node.name}"
            )
        ]

    raise RuntimeError("unknown AST node")


def compile_file(path: str) -> ProgramNode:
    try:
        with open(path, "rb") as file:
            source = file.read()
    except OSError as error:
        raise RuntimeError(str(error))

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    return parser.parse()


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--ast":
        print(
            "usage: python3 compiler.py --ast input.txt",
            file=sys.stderr,
        )
        return 1

    path = sys.argv[2]

    try:
        program = compile_file(path)

        for line in dump_ast(program):
            print(line)

        return 0

    except CompilationError as error:
        print(
            (
                f"compilation error: "
                f"line {error.line}:{error.column}: "
                f"{error.message}"
            ),
            file=sys.stderr,
        )
        return 1

    except RuntimeError as error:
        print(
            f"compilation error: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

import pytest
from unittest import TestCase
from js2py import js2py

class TestMyVisitor(TestCase):
    def setUp(self):
        pass

    def test_transform_StaticMemberExpression(self):
        self.fail()

    def test_transform_MemberExpression(self):
        self.fail()

    def test_transform_Object(self):
        self.assertEqual(js2py("this.foo"), "self.foo\n")

    def test_transform_ExportDefaultDeclaration(self):
        self.fail()

    def test_transform_FunctionExpression(self):
        self.fail()

    def test_transform_ImportDeclaration(self):
        self.assertEqual(js2py("import { thing } from \"location\""), "from location import thing\n")
        self.assertEqual(js2py("import { thing1, thing2 } from \"location\""), "from location import thing1, thing2\n")
        self.assertEqual(js2py("import * as mymod from \"location\""), "import location as mymod\n")

    def test_transform_MetaProperty(self):
        self.fail()

    def test_transform_ThisExpression(self):
        self.assertEqual(js2py("this.foo"), "self.foo\n")
        self.assertEqual(js2py("this.foo.bar"), "self.foo.bar\n")

    def test_transform_ReturnStatement(self):
        self.assertEqual(js2py("return"), "return None\n")
        self.assertEqual(js2py("return a"), "return a\n")
        self.assertEqual(js2py("return 1"), "return 1\n")

    # def test_transform_BlockStatement(self):
    #     self.fail()

    def test_transform_ThrowStatement(self):
        self.assertEqual(js2py("try { throw Error(\"hey\") } catch (e) { }"), "try:\n    raise Exception('hey')\nexcept e:\n    pass\n")

    def test_transform_AnonymousFunction(self):
        self.assertEqual(js2py("var x = function(a, b) { return a+b }"), "def Anonymous_0(a, b):\n    return a + b\n\n\nx = Anonymous_0\n")

    def test_transform_FunctionDeclaration(self):
        self.assertEqual(js2py("function foo(a, b) { return a+b }"), "def foo(a, b):\n    return a + b\n")

    def test_transform_AssignmentExpression(self):
        self.assertEqual(js2py("var x = 0"), "x = 0\n")
        self.assertEqual(js2py("let x = 0"), "x = 0\n")
        self.assertEqual(js2py("const x = 0"), "x = 0\n")

    def test_transform_Literal(self):
        self.assertEqual(js2py("1"), "1\n")
        self.assertEqual(js2py("'1'"), "'1'\n")
        self.assertEqual(js2py("'what'"), "'what'\n")

    def test_transform_RegexLiteral(self):
        self.assertEqual(js2py(r"/thing/"), "re.compile('thing')\n")

    def test_transform_NewExpression(self):
        self.assertEqual(js2py(r"thing = new Dog()"), "thing = Dog()\n")

    def test_transform_CallExpression(self):
        self.assertEqual(js2py("print('hello')"), "print('hello')\n")

    def test_transform_Identifier(self):
        self.assertEqual(js2py("thing"), "thing\n")

    def test_transform_ArrayExpression(self):
        self.assertEqual(js2py("[1,2,3,4]", "[1,2,3,4]\n"))

    def test_transform_Property(self):
        self.fail()

    def test_transform_ObjectExpression(self):
        assert js2py("d = { 'a' : 1, 'b' : 2}") in ["d = {'a': 1, 'b': 2}\n", "d = {'b': 2, 'a': 1}\n"]

    def test_transform_Program(self):
        self.fail()

    def test_transform_ExpressionStatement(self):
        self.fail()

    # def test_transform_VariableDeclarator(self):
    #     self.fail()

    def test_transform_VariableDeclaration(self):
        self.assertEqual(js2py("var x = 0"), "x = 0\n")
        self.assertEqual(js2py("var x = 0, y = 1"), "x = 0\ny = 1\n")

    def test_transform_IfStatement(self):
        self.assertEqual(js2py("""if (1) { return 1 }"""), """if 1:\n    return 1\n""")
        self.assertEqual(js2py("""if (1) {return 1} else { return 2 }"""), """if 1:\n    return 1\nelse:\n    return 2\n""")
        self.assertEqual(js2py("""if (1) {return 1} else if (2) { return 2 }"""), """if 1:\n    return 1\nelif 2:\n    return 2\n""")
        self.assertEqual(js2py("""if (1) {return 1} else if (2) { return 2 } else { return 3 }"""), """if 1:\n    return 1\nelif 2:\n    return 2\nelse:\n    return 3\n""")

    def test_transform_ForInStatement(self):
        self.assertEqual(js2py("""array1 = ['a', 'b', 'c']; for (element in array1) {  console.log(element); }"""), """array1 = ['a', 'b', 'c']\nfor element in array1:\n    console.log(element)\n""")

    def test_transform_ForOfStatement(self):
        self.assertEqual(js2py("""array1 = ['a', 'b', 'c']; for (element of array1) {  console.log(element); }"""), """array1 = ['a', 'b', 'c']\nfor element in array1:\n    console.log(element)\n""")

    def test_transform_ForStatement(self):
        self.assertEqual(js2py("""for (i = 0; i < 5; i++) { print(i); }"""), "i = 0\nwhile i < 5:\n    print(i)\n    i += 1\n")
        self.assertEqual(js2py("""for (i = 2; i < 5; i++) { print(i); }"""), "i = 2\nwhile i < 5:\n    print(i)\n    i += 1\n")
        self.assertEqual(js2py("""for (i = 2; i < 5; i += 3) { print(i); }"""), "i = 2\nwhile i < 5:\n    print(i)\n    i += 3\n")
        self.assertEqual(js2py("""for (i = 2, j=3; i < 5; i += 3) { print(i); }"""), "i = 2\nj = 3\nwhile i < 5:\n    print(i)\n    i += 3\n")
        self.assertEqual(js2py("""for (i = 2, j=3; i < 5; i += 3, j += 1) { print(i); }"""), "i = 2\nj = 3\nwhile i < 5:\n    print(i)\n    i += 3\n    j += 1\n")
        self.assertEqual(js2py("""for (; i < 5; i += 3, j += 1) { print(i); }"""),
                         "while i < 5:\n    print(i)\n    i += 3\n    j += 1\n")

    def test_transform_WhileStatement(self):
        self.assertEqual(js2py("""while (1) {print('hi')}"""), "while 1:\n    print('hi')\n")

    def test_transform_EmptyStatement(self):
        self.fail()

    def test_transform_UpdateExpression(self):
        self.assertEqual(js2py("j += 3"), "j += 3\n")
        self.assertEqual(js2py("j++"), "j += 1\n")
        self.assertEqual(js2py("j--"), "j -= 1\n")
        self.assertEqual(js2py("j-=2"), "j -= 2\n")

    def test_transform_UnaryExpression(self):
        self.assertEqual(js2py("-x"), "-x\n")
        self.assertEqual(js2py("~x"), "~x\n")
        self.assertEqual(js2py("+x"), "+x\n")
        self.assertEqual(js2py("-(x + 1)"), "-(x + 1)\n")

    def test_transform_LogicalExpression(self):
        self.assertEqual(js2py("(a+b) || (c + d) && (e + f)"), "a + b or c + d and e + f\n")

    def test_transform_ConditionalExpression(self):
        self.assertEqual(js2py("x > 0 ? 1 : 2"), "1 if x > 0 else 2\n")
        self.assertEqual(js2py("x > 0 ? 1 : (x > 2 ? 3 : 4)"), "1 if x > 0 else 3 if x > 2 else 4\n")
        self.assertEqual(js2py("x > 0 ? (x > 2 ? 3 : 4) : 1"), "(3 if x > 2 else 4) if x > 0 else 1\n")

    def test_transform_YieldExpression(self):
        self.fail()

    def test_transform_SequenceExpression(self):
        self.fail()

    def test_transform_BreakStatement(self):
        self.assertEqual(js2py("while (1) { break }"),
                         "while 1:\n    break\n")

    def test_transform_SwitchStatement(self):
        self.assertEqual(js2py("""
switch (s) {
case 1:
    console.log(hi);
case 2:
case 3:
    console.log(hello);
}"""),"if s == 1:\n    console.log(hi)\nif s == 2 or s == 3:\n    console.log(hello)\n\n")

    def test_transform_ArrowFunctionExpression(self):
        self.assertEqual(js2py("var x = (a, b) => a+b"),
                         "def Anonymous_0(a, b):\n    return a + b\n\n\nx = Anonymous_0\n")

    def test_transform_ClassDeclaration(self):
        self.fail()

    def test_transform_ClassBody(self):
        self.fail()

    def test_transform_MethodDefinition(self):
        self.fail()

    def test_transform_ContinueStatement(self):
        self.fail()

    def test_transform_TryStatement(self):
        self.fail()

    def test_transform_CatchClause(self):
        self.fail()

    def test_transform_BinaryExpression(self):
        self.assertEqual(js2py("a in [1,2,3]"), "j in [1,2,3]\n")
        self.assertEqual(js2py("j instanceof int"), "isinstance(j, int)\n")
        self.assertEqual(js2py("a + b + c + d"), "a + b + c + d\n")
        self.assertEqual(js2py("a - 1 - 2 - b"), "a - 1 - 2 - b\n")
        self.assertEqual(js2py("a * b * c"), "a * b * c\n")
        self.assertEqual(js2py("a / b"), "a / b\n")
        self.assertEqual(js2py("a % b"), "a % b\n")
        self.assertEqual(js2py("a ** b"), "a ** b\n")
        self.assertEqual(js2py("a | b"), "a | b\n")
        self.assertEqual(js2py("a ^ b"), "a ^ b\n")
        self.assertEqual(js2py("a & b"), "a & b\n")
        self.assertEqual(js2py("a, b") == "a == b\n")
        self.assertEqual(js2py("a != b"), "a != b\n")
        self.assertEqual(js2py("a === b"), "a == b\n")
        self.assertEqual(js2py("a !== b"), "a != b\n")
        self.assertEqual(js2py("a < b"), "a < b\n")
        self.assertEqual(js2py("a > b"), "a > b\n")
        self.assertEqual(js2py("a <= b"), "a <= b\n")
        self.assertEqual(js2py("a << b"), "a << b\n")
        self.assertEqual(js2py("a >> b"), "a >> b\n")
        self.assertEqual(js2py("a >>> b"), "a >> b\n")
        self.assertEqual(js2py("a || b"), "a or b\n")
        self.assertEqual(js2py("a && b"), "a and b\n")
        self.assertEqual(js2py("a >= b"), "a >= b\n")
        self.assertEqual(js2py("a <= b"), "a <= b\n")
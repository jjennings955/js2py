import pytest
from unittest import TestCase
from js2py import js2py

class TestMyVisitor(TestCase):
    def setUp(self):
        pass

    def test_transform_StaticMemberExpression(self):
        self.assertEqual(js2py("console.log(1)"), "console.log(1)\n")

    def test_transform_MemberExpression(self):
        self.assertEqual(js2py("a.b"), "a.b\n")

    def test_transform_Object(self):
        self.assertEqual(js2py("this.foo"), "self.foo\n")

    def test_transform_ExportDefaultDeclaration(self):
        self.fail()

    def test_transform_FunctionExpression(self):
        self.assertEqual(js2py("x = function() { console.log('hi'); }"), "def Anonymous_0():\n    console.log('hi')\n\n\nx = Anonymous_0\n")
        self.assertEqual(js2py("x = (function() { console.log('hi'); })()"),
                         "def Anonymous_0():\n    console.log('hi')\n\n\nx = Anonymous_0()\n")

    def test_transform_ImportDeclaration(self):
        self.assertEqual(js2py("import { thing } from \"location\""), "from location import thing\n")
        self.assertEqual(js2py("import { thing1, thing2 } from \"location\""), "from location import thing1, thing2\n")
        self.assertEqual(js2py("import * as mymod from \"location\""), "import location as mymod\n")

    def test_transform_MetaProperty(self):
        self.skipTest("I don't know what a metaproperty is")

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
        self.assertEqual(js2py("throw Error()"), "raise Exception()\n")
        self.assertEqual(js2py("throw SomeOtherException()"), "raise SomeOtherException()\n")

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
        self.assertEqual(js2py("'1'"), '"""1"""\n')
        self.assertEqual(js2py("x = \"1\""), "x = '1'\n")
        self.assertEqual(js2py("null"), "None\n")


    def test_transform_RegexLiteral(self):
        self.assertEqual(js2py(r"/thing/"), "re.compile('thing')\n")

    def test_transform_NewExpression(self):
        self.assertEqual(js2py(r"thing = new Dog()"), "thing = Dog()\n")

    def test_transform_CallExpression(self):
        self.assertEqual(js2py("print('hello')"), "print('hello')\n")

    def test_transform_Identifier(self):
        self.assertEqual(js2py("thing"), "thing\n")

    def test_transform_ArrayExpression(self):
        self.assertEqual(js2py("[1,2,3,4]"), "[1, 2, 3, 4]\n")
        self.assertEqual(js2py("[a,b,3,4]"), "[a, b, 3, 4]\n")
        self.assertEqual(js2py("[a,b,3,4]"), "[a, b, 3, 4]\n")
        self.assertEqual(js2py("[]"), "[]\n")
        self.assertEqual(js2py("[[], [1], [1,2], [1,2,3]]"), "[[], [1], [1, 2], [1, 2, 3]]\n")

    def test_transform_Property(self):
        self.assertEqual(js2py("d = { 1 : 2  }"),  "d = {(1): 2}\n")
        self.assertEqual(js2py("d = { 'a' : 2  }"), "d = {'a': 2}\n")
        self.assertEqual(js2py("d = { console : 2 }"), "d = {console: 2}\n")

    def test_transform_ObjectExpression(self):
        assert js2py("d = { 'a' : 1, 'b' : 2}") in ["d = {'a': 1, 'b': 2}\n", "d = {'b': 2, 'a': 1}\n"]

    def test_transform_Program(self):
        self.assertTrue(True)

    def test_transform_ExpressionStatement(self):
        self.assertTrue(True)

    def test_transform_VariableDeclarator(self):
        self.assertEqual(js2py("var x"), "x = None\n")

    def test_transform_VariableDeclaration(self):
        self.assertEqual(js2py("var x = 0"), "x = 0\n")
        self.assertEqual(js2py("var x = 0, y = 1"), "x = 0\ny = 1\n")

    def test_transform_IfStatement(self):
        self.assertEqual(js2py("""if (1) { return 1 }"""), """if 1:\n    return 1\n""")
        self.assertEqual(js2py("""if (1) {return 1} else { return 2 }"""), """if 1:\n    return 1\nelse:\n    return 2\n""")
        self.assertEqual(js2py("""if (1) {return 1} else if (2) { return 2 }"""), """if 1:\n    return 1\nelif 2:\n    return 2\n""")
        self.assertEqual(js2py("""if (1) {return 1} else if (2) { return 2 } else { return 3 }"""), """if 1:\n    return 1\nelif 2:\n    return 2\nelse:\n    return 3\n""")
        self.assertEqual(js2py("""if (1) { foo(); foo(); return 1}"""),
                         """if 1:\n    foo()\n    foo()\n    return 1\n""")

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

    # def test_transform_EmptyStatement(self):
    #     # self.fail()

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
        self.assertEqual(js2py("delete a"), "del a\n")
        self.assertEqual(js2py("delete a[0]"), "del a[0]\n")

    def test_transform_LogicalExpression(self):
        self.assertEqual(js2py("(a+b) || (c + d) && (e + f)"), "a + b or c + d and e + f\n")
        self.assertEqual(js2py("a || b"), "a or b\n")

    def test_transform_ConditionalExpression(self):
        self.assertEqual(js2py("x > 0 ? 1 : 2"), "1 if x > 0 else 2\n")
        self.assertEqual(js2py("x > 0 ? 1 : (x > 2 ? 3 : 4)"), "1 if x > 0 else 3 if x > 2 else 4\n")
        self.assertEqual(js2py("x > 0 ? (x > 2 ? 3 : 4) : 1"), "(3 if x > 2 else 4) if x > 0 else 1\n")

    def test_transform_YieldExpression(self):
        self.assertEqual(js2py("function* foo() { for (i = 0; i < 10; i++) { yield i } }"), "def foo():\n    i = 0\n    while i < 10:\n        yield i\n        i += 1\n")

    def test_transform_SequenceExpression(self):
        self.assertEqual(js2py("x = 3, b = 2, c = 4"), "x = 3\nb = 2\nc = 4\n")

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
}"""),"if s == 1:\n    console.log(hi)\nelif s == 2 or s == 3:\n    console.log(hello)\n")
        self.assertEqual(js2py("""
    switch (s) {
    case 1:
        console.log(hi);
    case 2:
    case 3:
        console.log(hello);
    default:
        console.log(hey);
    }"""), "if s == 1:\n    console.log(hi)\nelif s == 2 or s == 3:\n    console.log(hello)\nconsole.log(hey)\n")

    def test_transform_ArrowFunctionExpression(self):
        self.assertEqual(js2py("var x = (a, b) => a+b"),
                         "def Anonymous_0(a, b):\n    return a + b\n\n\nx = Anonymous_0\n")

    def test_transform_ClassDeclaration(self):
        self.assertEqual(js2py("class A { }"),
                         "class A:\n    pass\n")

    def test_transform_ClassBody(self):
        self.assertEqual(js2py("class A { constructor() { } }"),
                         "class A:\n\n    def __init__(self):\n        pass\n")

    def test_transform_MethodDefinition(self):
        self.assertEqual(js2py("class A {\n    constructor() { }\n    calcArea() { return 3*5 + a } }\n"),
                         "class A:\n\n    def __init__(self):\n        pass\n\n    def calcArea(self):\n        return 3 * 5 + a\n")

    def test_transform_ContinueStatement(self):
        self.assertEqual(js2py("while (1) { continue }"), "while 1:\n    continue\n")

    def test_TryCatchFinally(self):
        self.assertEqual(js2py("try { something() } catch (e) { }"), "try:\n    something()\nexcept Exception as e:\n    pass\n")
        self.assertEqual(js2py("try { something() } catch (e) { } finally { something2() }"),
                         "try:\n    something()\nexcept Exception as e:\n    pass\nfinally:\n    something2()\n")
        self.assertEqual(js2py("try { something() } catch (e) { something1() } finally { something2() }"),
                         "try:\n    something()\nexcept Exception as e:\n    something1()\nfinally:\n    something2()\n")

    # def test_transform_CatchClause(self):
    #     self.fail()

    def test_transform_BinaryExpression(self):
        self.assertEqual(js2py("j in [1,2,3]"), "j in [1, 2, 3]\n")
        self.assertEqual(js2py("j in list_of_stuff"), "j in list_of_stuff\n")
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
        self.assertEqual(js2py("a == b"), "a == b\n")
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